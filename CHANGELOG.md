# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
このプロジェクトはセマンティックバージョニングに従います。

現在のバージョン: 0.1.0

## [Unreleased]

### 注意 / 既知の問題
- pipeline._get_max_date 内に実装ミスと思われる箇所があり（最後が `return date.fro` のような不完全な記述）、この関数の戻り値処理が未完了です。CI/レビューで修正が必要です。
- 一部モジュールの __init__（例: data/__init__.py）が空のままです。将来的に公開 API を整理して明示的にエクスポートする予定です。
- OpenAI 呼び出しに依存する AI 機能（news_nlp, regime_detector）は API キー（OPENAI_API_KEY もしくは関数引数）を必要とします。テスト時はモック化が推奨されます（モジュール内の _call_openai_api をパッチ可能に設計済み）。
- DuckDB のバージョン差分（例: executemany に空リストを渡せない挙動）に対するワークアラウンドを実装しています。将来の DuckDB バージョン変更による影響は注意してください。

### TODO / 今後の改善候補
- data パッケージの公開 API を整理して明示的にエクスポートする。
- pipeline モジュールの未完了部分を修正し、単体テストを追加する。
- エンドツーエンドの統合テスト（DuckDB の一時 DB を用いた ETL / AI パイプライン検証）を追加する。
- AI モデルやタイムウィンドウ等のパラメータを外部設定化して運用時に調整可能にする。

---

## [0.1.0] - 2026-04-01

初回リリース。以下の主要機能を実装・公開しました。

### Added
- パッケージ基盤
  - パッケージメタ情報: kabusys/__init__.py に __version__ = "0.1.0"、公開モジュール一覧を設定。
- 設定管理
  - 環境変数 / .env 自動ロード機能（config.py）
    - プロジェクトルートを .git / pyproject.toml から探索して .env と .env.local を自動読み込み。
    - 読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - .env のパースは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなどをサポート。
    - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 監視閾値 / 実行環境（development/paper_trading/live）等をプロパティ経由で取得。値検証（環境名・ログレベルの検証、必須キー未設定で例外）を行う。
- データプラットフォーム（DuckDB ベース）
  - calendar_management モジュール
    - market_calendar を利用した営業日判定ユーティリティ: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - DB データが無い場合は曜日ベース（週末）でフォールバックする動作を提供。
    - calendar_update_job: J-Quants からカレンダー差分を取得して冪等的に保存する夜間バッチ処理（バックフィル、安全性チェックあり）。
  - pipeline / ETL
    - ETLResult データクラス（pipeline.ETLResult）を定義し、ETL 実行結果の集約・シリアライズ機能を提供。
    - ETL の差分更新・バックフィル方針、品質チェックフレームワークとの連携方針を実装（quality モジュールとの接続点あり）。
    - kabusys.data.etl で ETLResult を再エクスポート。
- 研究（Research）モジュール
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を DuckDB SQL ベースで計算。データ不足時は None を返す設計。
    - calc_volatility: 20日 ATR（平均）、ATR 比率、20日平均売買代金、出来高比率などを計算。入力データ不足に対する None 処理あり。
    - calc_value: raw_financials から直近財務データを取得して PER / ROE を算出（EPS が 0 または欠如時は None）。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）に対する将来リターンを LEAD を使って一括計算。
    - calc_ic: factor と将来リターンの Spearman ランク相関（IC）を計算。レコード不足や分散 0 の場合は None を返す。
    - rank: 同順位の平均ランクを返すユーティリティ（数値丸めで ties の検出安定化）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - data.stats からの zscore_normalize を再エクスポート（research.__init__）。
- AI / ニュース解析
  - news_nlp モジュール
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON mode）へバッチで問い合わせて銘柄ごとのセンチメント（-1.0〜1.0）を算出。
    - タイムウィンドウは JST 基準（前日 15:00 ～ 当日 08:30）→ UTC 変換済みで DB クエリに利用。
    - チャンク処理（最大 20 銘柄/コール）、1 銘柄あたり最大記事数・文字数制限、レスポンス検証（JSON 抽出・キー検査・スコア数値化・クリッピング）を実装。
    - リトライ戦略: 429/ネットワーク/タイムアウト/5xx に対して指数バックオフでリトライ。非再試行エラーはスキップ（フェイルセーフ）。
    - 結果は ai_scores テーブルへ（対象コードのみ DELETE → INSERT で置換）安全に書き込み。
  - regime_detector モジュール
    - ETF 1321 の 200 日移動平均乖離（ma200_ratio）と news_nlp 由来のマクロセンチメントを重み付け（0.7 / 0.3）して日次の市場レジーム（bull/neutral/bear）を判定。
    - LLM 呼び出しは別実装の _call_openai_api を使用（モジュール間の結合を避ける設計）。
    - API エラー時は macro_sentiment を 0.0 にフォールバックして処理を継続。
    - 判定結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
- モジュール API 層
  - kabusys.ai.__init__ に score_news を公開。
  - kabusys.research.__init__ に主要なファクター関数と zscore_normalize 等を公開。
  - kabusys.data.etl で ETLResult を公開。

### Changed
- （初回リリースにつき変更履歴なし）

### Fixed
- （初回リリースにつき修正履歴なし）

### Security
- OpenAI API キー等の機密情報は環境変数経由で取得する設計。.env 自動ロードはデフォルトで有効だが、テスト等で無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。

---

署名:
kabusys チーム（自動生成ドキュメント）