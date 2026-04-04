# CHANGELOG

すべての注目すべき変更を記録します。  
このプロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の原則に準拠しています。

現在のバージョン: 0.1.0

## [Unreleased]
- なし

## [0.1.0] - 2026-04-04
初回リリース。

### 追加
- パッケージ基盤
  - kabusys パッケージを追加。__version__ を "0.1.0" として公開。
  - パッケージの公開インターフェースとして data, strategy, execution, monitoring を __all__ に定義。

- 設定管理
  - 環境変数 / .env の自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - .env /.env.local の優先順位制御（OS 環境変数を保護しつつ .env.local で上書き可能）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを追加。
  - POSIX 形式の .env パーサ実装（コメント、export プレフィックス、引用符内のエスケープ対応、インラインコメント処理）。
  - Settings クラスを実装し、J-Quants / kabu API / LINE / DB / 監視 / ログ等の設定プロパティを提供。
  - 設定値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と便利なブールプロパティ（is_live / is_paper / is_dev）を追加。

- AI（自然言語処理）
  - ニュースNLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を元に、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - バッチサイズ、記事数・文字数のトリム、タイムウィンドウ（JST基準）の計算ロジックを実装。
    - JSON Mode を想定したレスポンス検証と復元ロジック（余分な前後テキストから最外の {} を抽出）。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ（ログ出力付き）。
    - スコアの ±1.0 クリッピング、部分失敗時に他コードの既存スコアを保護する idempotent な DB 書き込み（DELETE → INSERT）。
    - テストしやすさのため OpenAI 呼び出しをラップ可能（_call_openai_api を patch 可能に設計）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースフィルタリング用キーワード群、最大記事数制限、OpenAI 呼び出し（gpt-4o-mini）とリトライ/フェイルセーフ戦略を実装。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）、API 失敗時は macro_sentiment=0.0 にフォールバック。
    - ルックアヘッドバイアス対策として datetime.today()/date.today() を参照せず、prices_daily クエリは target_date 未満のデータのみ参照。

- リサーチ / ファクター
  - kabusys.research パッケージを実装。
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）を計算。
    - calc_volatility: 20日 ATR / 相対ATR（atr_pct） / 20日平均売買代金 / 出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を取得して PER, ROE を計算（EPS=0/欠損は None）。
    - DuckDB を用いる SQL + Python の実装。データ不足時の None ハンドリング、ログ出力を備える。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効レコード < 3 の場合は None）。
    - rank: 同順位の平均ランク計算（丸めによる ties 検出改善）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー関数。
    - 外部ライブラリに依存しない実装（標準ライブラリ + DuckDB）。

- データ基盤（Data）
  - calendar_management モジュール:
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値を優先しつつ未登録日は曜日ベースでフォールバックする一貫性のあるロジック。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等で更新。バックフィル / 健全性チェックを実装。
  - ETL パイプライン（pipeline モジュール）
    - ETLResult dataclass を追加（ETL の取得数・保存数・品質問題・エラーを保持）。
    - 差分更新、backfill、品質チェック（quality モジュール連携）、idempotent な保存戦略を想定した設計。
    - DuckDB の互換性を考慮した実装（executemany の空リスト回避等）。
  - etl.py で ETLResult を公開再エクスポート。

### 変更（設計上の重要ポイント）
- ルックアヘッドバイアス防止のため、AI/リサーチ/ETL の主要関数は内部で date.today() や datetime.today() を参照せず、必ず caller が target_date を渡す設計。
- OpenAI 呼び出しはモジュールごとに独立したラッパ（_call_openai_api）を用意し、テスト時に差し替え可能。
- OpenAI 連携部分は JSON Mode を利用する前提だが、パース失敗時の復元ロジックを備える（堅牢化）。
- DuckDB のバージョン差異を考慮した実装（executemany 空リスト回避、LIST 型バインド回避など）。
- DB 書き込みは可能な限り冪等化（DELETE→INSERT、ON CONFLICT 等）して部分失敗による既存データ消失を防止。

### 修正
- 初リリースのため既知のバグ修正履歴はなし。

### セキュリティ
- 機密情報（OpenAI API キー等）は Settings 経由で環境変数から取得。自動 .env ロード機構は OS 環境変数を保護する設計。

---

注:
- 本 CHANGELOG はソースコードからの推測に基づく記述です。実際のリリースノートとして公開する場合は、開発履歴・コミットログ・リリース作業に基づく追記・修正を推奨します。