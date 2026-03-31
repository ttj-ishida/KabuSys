# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。セマンティックバージョニングに従います。

## [Unreleased]

- 今後の変更はここに記載します。

## [0.1.0] - 2026-03-31

初回リリース。

### 追加 (Added)

- パッケージ基盤
  - kabusys パッケージの初期公開。__version__ = "0.1.0" を設定。
  - パッケージの公開 API を __all__ で定義（data, strategy, execution, monitoring を想定）。

- 設定 / 環境変数管理 (kabusys.config)
  - .env / .env.local ファイルと OS 環境変数から設定を自動読込する機能を実装。
    - プロジェクトルートは .git または pyproject.toml を起点に探索して特定（CWD に依存しない）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能。
  - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント等に対応する堅牢な実装。
  - 環境変数保護（既存 OS 環境変数を protected として上書きを制御）対応。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 監視閾値 / 実行環境（development/paper_trading/live）等をプロパティとして取得。
    - env と log_level の妥当性チェックと専用プロパティ（is_live/is_paper/is_dev）を実装。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を集約して銘柄別にテキストを作成し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信してセンチメントスコアを取得。
    - JST のニュースウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を正しく計算する calc_news_window を提供。
    - 1 銘柄あたりの最大記事数・最大文字数でトリムする仕組みを導入（トークン制御）。
    - 最大 20 銘柄／チャンクでバッチ送信。429・ネットワーク断・タイムアウト・5xx に対する指数バックオフのリトライ実装。
    - レスポンスの厳格なバリデーション（JSON 抽出、results リスト・code/score の検証、スコアを ±1.0 でクリップ）。
    - 成功したコードのみ ai_scores テーブルに対して冪等的に置換（DELETE→INSERT）を行い、部分失敗で既存スコアを破壊しない。
    - API 呼び出し部分は差し替え可能に実装（テスト容易性を考慮）。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース由来の LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily から ma200 乖離を算出（target_date 未満のデータのみ使用しルックアヘッドを防止）。
    - raw_news をマクロキーワードでフィルタして OpenAI に投げ、マクロセンチメント（-1.0〜1.0）を取得。記事が無い場合は LLM を呼ばず 0.0 を使用。
    - OpenAI 呼び出しはリトライ/バックオフを備え、失敗時は macro_sentiment=0.0 にフォールバックして処理継続（フェイルセーフ）。
    - 計算したレジームは market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。

- データプラットフォーム (kabusys.data)
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar を用いた営業日判定ロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータが存在しない場合は曜日ベース（平日を営業日）でフォールバック。DB 登録あり→DB 値優先の一貫した挙動。
    - カレンダー差分取得ジョブ（calendar_update_job）を実装し、J-Quants クライアント経由で差分取得→冪等保存（バックフィル、健全性チェック含む）。
  - ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラスを提供し、ETL の取得数/保存数/品質問題/エラーを集約して返却。
    - 差分更新、バックフィル、品質チェック（kabusys.data.quality 想定）を行う設計。J-Quants クライアントを用いた取得/保存を想定。
    - kabusys.data.etl で pipeline.ETLResult を再エクスポート。

- リサーチ / ファクター (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率）、Value（PER, ROE）を DuckDB 上の SQL と Python 組合せで実装。
    - データ不足時の None 戻しやログ出力を整備。価格・財務テーブルのみ参照（外部発注 API へはアクセスしない）。
    - 計算結果は (date, code) をキーとする dict のリストで返却。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算（calc_forward_returns）: 指定ホライズン（デフォルト [1,5,21]）の終値ベースのリターンを計算。
    - IC 計算（calc_ic）: factor と将来リターンのスピアマンランク相関を算出（ties を平均ランクで処理）。
    - rank / factor_summary: ランク化ユーティリティと、count/mean/std/min/max/median を返す統計サマリーを実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

### 変更 (Changed)

- 初回リリースのため該当なし。

### 修正 (Fixed)

- 初回リリースのため該当なし。

### セキュリティ (Security)

- OpenAI API キーや各種機密情報は Settings を通じて環境変数から取得する設計。.env の自動読込は環境変数で無効化可能。

---

注記（設計上の重要ポイント）
- ルックアヘッドバイアス防止: AI スコアリングやレジーム判定は内部で datetime.today()/date.today() を直接参照せず、明示的な target_date を受け取る設計。
- フェイルセーフ: 外部 API（OpenAI / J-Quants 等）の一時失敗時は部分的にフォールバックして処理を継続する（例: macro_sentiment=0.0、該当チャンクスキップ）。
- 冪等性: DB 書き込みは基本的に冪等操作を意識（DELETE→INSERT や ON CONFLICT を想定）しているため、再実行に耐える。
- テスト容易性: OpenAI 呼び出しや内部 API 呼び出し箇所を差し替え可能（モック化）にしている。

[0.1.0]: https://example.com/releases/0.1.0