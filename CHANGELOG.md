# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
このファイルはコードベースの内容から推測して作成した初期リリース向けの変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。下記の主要な機能群とユーティリティを実装しています。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。モジュール公開: data, strategy, execution, monitoring。
- 設定 / 環境変数管理（kabusys.config）
  - .env / .env.local 自動読み込み機能（プロジェクトルートは .git または pyproject.toml を探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パーサの実装：コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - 環境設定ラッパー Settings を提供。J-Quants / kabuステーション / Slack / DB パス / 環境種別（development/paper_trading/live）/ログレベルなどのプロパティを定義。必須値未設定時は ValueError を送出。
  - OS 環境変数を保護するための上書きポリシー（protected set）を採用。
- AI モジュール（kabusys.ai）
  - news_nlp.score_news
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信して銘柄別センチメント（ai_scores）を算出・保存。
    - バッチサイズ、記事数・文字数制限、チャンクごとのリトライ（429/ネットワーク/タイムアウト/5xx）とエラーハンドリングを実装。
    - レスポンスのバリデーションとスコアの ±1.0 クリップ。DuckDB に対する安全な DELETE → INSERT の冪等保存処理。
    - calc_news_window ユーティリティ（JST 時刻窓の UTC 変換）を提供。
  - regime_detector.score_regime
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定・保存。
    - prices_daily / raw_news を参照、OpenAI 呼び出しは専用実装でモジュール間の結合を避ける設計。
    - API リトライ/バックオフ、フェイルセーフ（API 失敗時 macro_sentiment=0.0）を実装。DB 書き込みは冪等（BEGIN/DELETE/INSERT/COMMIT）。
- 研究・ファクター（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比を計算。
    - calc_value: raw_financials から最新財務データを結合して PER, ROE を算出。
    - 全関数は DuckDB（prices_daily / raw_financials）を参照し、外部 API に依存しない実装。
  - feature_exploration:
    - calc_forward_returns: 指定基準日から複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: スピアマンのランク相関（IC）を計算するユーティリティ。
    - rank: 平均ランク（ties は平均ランク）を返す関数（丸め処理で浮動小数点の ties を安定化）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
- データプラットフォーム（kabusys.data）
  - calendar_management:
    - market_calendar を利用した営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 未取得時の曜日ベースフォールバック、最大探索日数制限、カレンダーバックフィル/健全性チェックを実装。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存（fetch/save 統合、エラーハンドリング）。
  - pipeline / etl:
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - ETL の内部ユーティリティ（テーブル存在確認、最大日付取得、取得範囲調整等）を実装。差分更新・バックフィル・品質チェック設計方針を反映。

### Changed
- （初回リリースのため該当なし）

### Fixed
- .env 行パーサの堅牢化
  - export プレフィックス、引用符内のバックスラッシュエスケープ、インラインコメントの条件付き認識などの処理を追加し、実運用の .env 形式差異に耐性を持たせた。

### Security
- 環境変数の必須チェック（API キーや Slack トークン等）を Settings 側で行い、未設定時には明確なエラーメッセージで ValueError を送出。
- .env 自動ロード時に既存の OS 環境変数を protected set として保護する設計を採用。

### Performance & Reliability
- OpenAI 呼び出しに対して指数バックオフとリトライ、HTTP 5xx の扱い分け、最大試行回数を実装し、外部 API の一時障害を緩和。
- DuckDB へのバルク操作で、空パラメータの executemany を避けるガード実装（DuckDB 互換性対策）。
- LLM 応答のパース失敗や未知コードは無害にスキップして部分成功を保持するフェイルセーフ。

### Documentation
- 各モジュールに詳細な docstring を追加。処理フロー、設計方針、フェイルセーフ動作、ルックアヘッドバイアス防止（内部で date.today()/datetime.today() を直接参照しない）等を明記。

### Known limitations / Notes
- OpenAI API キー（OPENAI_API_KEY）の提供が必須。score_news/score_regime は API キー未提供時に ValueError を発生させる。
- DuckDB のバージョン依存挙動（リスト型バインドや executemany の空リスト挙動）に注意。実運用では DuckDB のバージョン互換性確認を推奨。
- 一部の関数（ETL の上位 pipeline 実行フローや jquants_client 実体）は外部モジュールに依存しており、該当クライアントの実装・設定が必要。
- strategy / execution / monitoring パッケージの公開は行われているが、このリリースでは内部実装の一部のみが含まれる（将来的な拡張予定）。

---

貢献・改善案・バグ報告は issue を通じてお知らせください。次のリリースでは以下を検討しています:
- ai モジュールの追加検証ロジックとモック用フックの整備（テスト容易性向上）
- ETL の具体的な pipeline 実行関数の公開 API と CLI の提供
- Slack 通知・監視用 hooks（monitoring）実装

-----