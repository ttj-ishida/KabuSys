CHANGELOG
=========
（このファイルは Keep a Changelog の形式に準拠しています。重要な変更点を日本語で記載しています。）

## [Unreleased]
### Added
- news_nlp モジュールの処理フロー実装の続き・安定化（OpenAI APIとのバッチ送信・リトライ・レスポンス検証は実装済みだが、記事集計後の一部処理が未完了のため最終化を予定）。
- unit/integration テスト追加予定（research / portfolio 周りの計算ロジックに対するテスト整備を想定）。

### Changed
- news_nlp のエラーハンドリングと部分コミット（ai_scores へ書き込む際の部分更新ロジック）をさらに堅牢化予定。

### Known issues
- src/kabusys/ai/news_nlp.py の一部関数がファイル切断（末尾の処理が未完）になっており、実運用前に完了が必要。

---

## [0.1.0] - 2026-04-16
### Added
- 基本アプリケーション初期リリース（バージョン 0.1.0）。
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。スレッドベースで ExecutionEngine を起動・監視。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite DB を使用して本番 DB と完全分離（PAPER_TRADING_SQLITE_PATH により上書き可能）。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - エンジン停止フラグ（data/stop_requested.flag）検知による安全停止処理と execution.pid ファイル取り扱い。
- 監視用スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループを提供。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV に依存せず本番 sqlite_path を使用してデータを収集。
    - 停止フラグ検出でループを終了し、例外発生時もログに記録して次回ポーリングに移行するフェイルセーフ実装。
- 設定管理
  - config.py
    - .env 自動ロード機能（プロジェクトルート (.git または pyproject.toml) を検出して .env / .env.local を読み込み）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - .env パーサーが export プレフィックス、クォート（シングル/ダブル）とバックスラッシュエスケープ、コメント処理に対応。
    - Settings クラスで主要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, PAPER_FILL_MODE 等）をプロパティで提供。値検証（enum など）を実装。
- ユーティリティ
  - utils/process_priority.py
    - cross-platform なプロセス優先度設定（Windows / POSIX 対応）を実装。AccessDenied 等の例外はログ警告で無視する堅牢設計。
    - CPU affinity 設定関数 set_cpu_affinity を追加。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルから候補選定（スコア降順、signal_rank によるタイブレーク）。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全スコア 0 の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap：セクター集中上限チェック（既存保有のセクター比率が上限を超える場合に新規候補を除外）。unknown セクターは除外対象外。
    - calc_regime_multiplier：市場レジームに応じた投下資金乗数（bull/neutral/bear のマップ。未知レジームは警告して 1.0 でフォールバック）。
    - 一部 TODO（価格欠損時のフォールバック戦略）を注記。
  - portfolio/position_sizing.py
    - calc_position_sizes：allocation_method（"risk_based" / "equal" / "score"）に基づく株数算出。
    - 単元（lot_size）丸め、1銘柄上限（max_position_pct）や aggregate cap（available_cash）を考慮したスケーリング、コストバッファ（手数料・スリッページ考慮）を実装。
    - aggregate スケールダウン時の残差配分アルゴリズム（lot 単位で fractional 残差順に追加配分）を実装。
    - 設計上の拡張点（銘柄別 lot_size）を注記。
- 研究・ファクター計算
  - research/factor_research.py
    - calc_momentum：1/3/6 ヶ月リターン、MA200 乖離を prices_daily から計算（DuckDB を利用）。
    - calc_volatility：20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value：raw_financials から最新財務データを参照し PER/ROE を算出。
    - 各関数ともにデータ不足時の None ハンドリングを実装。
  - research/feature_exploration.py
    - calc_forward_returns：複数ホライズンの将来リターンを一度の DuckDB クエリで取得（horizons の検証あり）。
    - calc_ic：スピアマンランク相関（Information Coefficient）を実装（null/非有限値の除外、少数データ時は None）。
    - rank / factor_summary：ランク付け・基本統計量計算を純粋関数で提供。
  - research/__init__.py にて公開 API を整備（zscore_normalize を含む）。
- AI ニューススコアリング
  - ai/news_nlp.py
    - raw_news を銘柄別に集約し、OpenAI API（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメントスコアを生成する設計を追加。
    - バッチサイズ、トークン肥大対策（1銘柄あたり記事数/文字数制限）、最大リトライロジック（429・ネットワーク・5xx 対応の指数バックオフ）を実装。
    - 出力 JSON の厳密検証、スコアの ±1.0 クリップ、部分成功時の ai_scores 部分置換（DELETE → INSERT）方針を採用。
    - OpenAI API キー解決（引数または OPENAI_API_KEY 環境変数）と未設定時の ValueError。
    - ※ファイル末尾は未完の個所があり、集約後のループ処理など一部実装が残っている。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証用の CLI レポート生成ツールを追加。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等の計算、閾値による PASS/FAIL 判定を出力（閾値はファイル内定数で定義）。
    - 日付指定 --from / --to、--db オプション、PAPER_TRADING_SQLITE_PATH 環境変数優先解決に対応。
    - P95 計算、欠損データ時の N/A 表示、SQLite のテーブル欠損（OperationalError）を安全に扱うフォールトトレラント実装。
- パッケージ初期化
  - kabusys/__init__.py に __version__ = "0.1.0" を追加し、主要サブパッケージを __all__ に登録。

### Changed
- なし（初回公開のため「追加」中心）。

### Fixed
- なし（初回公開）。

### Notes / Design decisions
- DB 操作: DuckDB を分析用に使用し、SQLite はモニタリング/トレードログ保存に使用する設計。paper_trading 環境は専用 SQLite を使用して本番 DB を汚さない。
- 実行コンポーネントは OS のプロセス優先度設定を最初に行い、実行中の安定性を優先する。権限不足や未対応 OS の場合は警告ログでスキップ。
- 設計方針として、研究・ツール・ニュース NLP は「本番取引 API にはアクセスしない」ことを明確化（フェイルセーフかつリードオンリーな分析基盤）。
- 一部モジュールに TODO コメントあり（価格欠損時のフォールバック、銘柄別 lot_size 管理など）。今後の改良ポイントとして留意。

---

（変更履歴にはソースコードから推測可能な機能・仕様・既知の未完実装を記載しています。実際のコミット履歴やタグ付けと照合して必要に応じて調整してください。）