# Changelog

すべての注記は Keep a Changelog 準拠の形式で記載しています。  
このリポジトリの初回リリースとして、以下の機能群を追加しました。

## [Unreleased]
（現在なし）

## [0.1.0] - 2026-04-01
初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - パッケージ API のエクスポート指定: data, strategy, execution, monitoring（strategy/execution/monitoring の実装は今回の差分中では未提供）。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env / .env.local ファイルおよび OS 環境変数から設定を自動読み込みする仕組みを追加。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）を実装し、CWD に依存しない自動読み込みを実現。
  - .env パーサの実装（コメント・export プレフィックス・シングル/ダブルクォートとエスケープ処理・インラインコメントの扱い等に対応）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - 環境変数取得ヘルパ _require() を実装（未設定時は ValueError を発生）。
  - Settings クラスを追加し、J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / システム環境などのプロパティを提供。デフォルト値や妥当性チェック（KABUSYS_ENV, LOG_LEVEL）を備える。

- AI ニュース/NLP (src/kabusys/ai/*.py)
  - ニュースセンチメント（銘柄単位）スコアリング: score_news を実装
    - 対象ウィンドウ（JST 基準：前日 15:00 ～ 当日 08:30）計算（calc_news_window）。
    - raw_news / news_symbols から銘柄ごとに記事を集約（1銘柄あたり記事数・文字数上限あり）。
    - OpenAI (gpt-4o-mini) を JSON mode で呼び出し、バッチ（最大 20 銘柄/コール）で評価。
    - レスポンスの厳密なバリデーションとスコアクリッピング（±1.0）。
    - エラー・レート制限・ネットワーク断・5xx に対する指数バックオフリトライを実装。フェイルセーフとして失敗時はそのチャンクをスキップし処理継続。
    - 成功スコアのみ ai_scores テーブルに冪等（DELETE → INSERT）で書き込み。DuckDB の executemany の制約を回避する実装（空リストを渡さないチェック）。
    - テスト容易性を考慮し、内部の OpenAI 呼び出し関数は patch による差し替えが可能。

  - マクロセンチメントと ETF 指標を組み合わせた市場レジーム判定: score_regime を実装（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（ウエイト 70%）とマクロニュース LLM センチメント（ウエイト 30%）を合成して regime_score を算出し market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出は news_nlp の窓関数 calc_news_window を利用。
    - OpenAI 呼び出しは専用実装で行い、API エラー発生時は macro_sentiment = 0.0 とするフォールバックを採用。
    - 冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）と例外時の ROLLBACK 保護。

- リサーチ / ファクター計算 (src/kabusys/research/*.py)
  - factor_research モジュールを追加（モメンタム / ボラティリティ / バリュー）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None を返す挙動）。
    - calc_volatility: 20 日 ATR（平均）・相対 ATR・20 日平均売買代金・出来高比率。
    - calc_value: raw_financials からの最新財務データと株価を結合して PER / ROE を計算。
    - 全関数は DuckDB の prices_daily / raw_financials テーブルのみ参照し、外部 API にはアクセスしない設計。
    - 結果は (date, code) を含む dict のリストとして返す。
  - feature_exploration モジュールを追加
    - calc_forward_returns: 指定日から各ホライズン（デフォルト 1,5,21）までの将来リターンを計算（不足時は None）。
    - calc_ic: factor と forward returns の Spearman ランク相関（IC）を計算（有効レコード <3 の場合は None）。
    - rank / factor_summary: ランク化と統計サマリー（count/mean/std/min/max/median）を提供。
  - research パッケージの __init__ で上記関数群を公開。

- データプラットフォーム / カレンダー (src/kabusys/data/*.py)
  - calendar_management モジュールを追加
    - market_calendar テーブルを使った営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータがない場合は曜日ベース（土日を非営業日）でフォールバックする一貫した振る舞いを採用。
    - next/prev_trading_day の探索は最大 _MAX_SEARCH_DAYS（60）まで制限し、無限ループを防止。
    - calendar_update_job: J-Quants クライアントから差分取得・バックフィル（直近 _BACKFILL_DAYS）・健全性チェック（最終日が過度に将来の場合はスキップ）・冪等保存の夜間バッチ実装。
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - ETLResult dataclass を実装し、ETL の取得数/保存数・品質問題・エラーを格納。to_dict() で品質問題を dict に変換して出力可能に。
    - 差分更新・バックフィル・品質チェックを設計方針として文書化（実際の pipeline 実行ロジックは jquants_client や quality を用いる想定）。
  - etl モジュール（src/kabusys/data/etl.py）で ETLResult を再エクスポート。
  - data パッケージ内で jquants_client を想定した連携を行う設計（実装は外部モジュールとして分離）。

### 修正 (Changed)
- 設計上の注意・堅牢性強化
  - AI モジュール・news_nlp と regime_detector でルックアヘッドバイアス防止のため date.today()/datetime.today() を直接参照しない設計を採用（target_date に依存）。
  - OpenAI 呼び出し共通部分は内部で明確に分離し、テストで差し替えやすくした（unittest.mock.patch を想定）。
  - DuckDB の挙動（executemany の空リスト不可等）に合わせた実装で互換性を確保。

### 修正 (Fixed)
- N/A（初回リリースのため既知のバグ修正はなし）

### 既知の問題 / 注意点 (Known Issues / Notes)
- pipeline._get_max_date の末尾が不完全（差分中の切り取りにより "return date.fro" のような未完の行が存在）で、このままでは該当ファイルのパース/実行時に構文エラーになる可能性があります。リリース前にファイル末尾の修正（正しい return 処理）を要確認。
- strategy / execution / monitoring モジュールはパッケージの __all__ に含まれるが、今回提示された差分では実装が含まれていません。これらは今後のリリースで追加予定。
- OpenAI API 周りは gpt-4o-mini を想定し JSON mode を利用するため、実行には有効な OPENAI_API_KEY が必要。API レスポンスは厳密な JSON を期待するが、フォールバックとして一部の解析ロジック（最外の {} を抽出する等）を実装しているものの、完全ではない場合がある。
- .env パーサは多くのケースに対応するが、極端に複雑なシェル式の展開（変数展開やコマンド代入など）はサポートしない。

### セキュリティ (Security)
- 現時点でセキュリティに関する特別なフィックスはありません。環境変数管理では OS 環境変数を protected として .env による上書きを抑止する挙動を採用しています。

---

今後の予定（例）
- strategy / execution / monitoring の実装と公開。
- pipeline の残り実装とパイプライン実行用 CLI /ジョブ化。
- 単体テスト補強と CI の追加。
- pipeline._get_max_date 周りのコード整備とその他軽微なバグ修正。

貢献・バグ報告は Issue を立ててください。