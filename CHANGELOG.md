Keep a Changelog形式で本リポジトリの変更履歴をコード内容から推測して日本語で作成しました。
以下はパッケージバージョン 0.1.0 相当の初期リリース想定の変更ログです。

CHANGELOG.md
============
全ての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------
（現在未リリースの変更はありません）

[0.1.0] - 2026-04-13
-------------------
Added
- 全体
  - 初版リリース。KabuSys 自動売買フレームワークの基礎機能を実装。
  - パッケージバージョンを __version__ = "0.1.0" として定義。

- 環境設定 / 起動
  - 環境変数読み込み実装（kabusys.config）
    - プロジェクトルートを .git または pyproject.toml から自動検出し、.env / .env.local を読み込む自動ローダーを実装。
    - OS 環境変数を保護するための上書きルール（.env.local は上書き可、.env は未設定のみセット）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード停止機能を追加。
    - 複雑な .env 行のパースを行う関数（クォート、エスケープ、コメント処理）を実装。
    - Settings クラスで多数の設定プロパティを提供（DBパス、PID/KILLファイル、閾値、Paper Trading 設定、API トークン等）。
    - PAPER_FILL_MODE や KABUSYS_ENV / LOG_LEVEL 等の値検証を実装（不正値は ValueError）。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト60秒）。不正値はデフォルトにフォールバックして警告出力。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する仕様。
    - 起動時にプロセス優先度を "high" に設定（utils のユーティリティを使用）。
    - SQLite / DuckDB の接続確立とクリーンなクローズを保証。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory を利用してブローカークライアントを生成（Paper 時は Mock を使用する想定）。
    - OrderRepository、OrderManager、RiskManager（RiskConfig）、Reconciler 等の組み立てを実装。
    - ExecutionEngine を構築して run_session を実行。DB（SQLite / DuckDB）は finally でクローズ。

- モニタリング / ツール
  - 監視 DB 初期化ユーティリティ（init_monitoring_db）を呼び出して監視テーブルの冪等初期化を実施。
  - tools/paper_verification_report.py
    - Paper Trading の検証レポートを生成する CLI ツールを実装。
    - 指標（稼働率、注文成功率、送信率、P95 レイテンシ等）の集計クエリを実装。
    - 閾値による PASS/FAIL 判定と整形された標準出力レポートを出力。
    - 日付フィルタ、DB パスオーバーライドオプション（--db）に対応。
    - データ欠損やテーブル未存在時に安全にフォールバックするハンドリングを実装（OperationalError を捕捉）。

- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio
    - portfolio_builder:
      - select_candidates: スコア降順＋signal_rank によるタイブレークで候補選定。
      - calc_equal_weights / calc_score_weights: 重み算出（score が全て 0 の場合は等分配へフォールバックして警告）。
    - risk_adjustment:
      - apply_sector_cap: セクター集中制限を適用して候補を除外（"unknown" セクターは無視）。
      - calc_regime_multiplier: 市場レジームに応じた投下比率乗数を返す（bull/neutral/bear、未知レジームは警告のうえ 1.0 でフォールバック）。
    - position_sizing:
      - calc_position_sizes: 重み・候補・ポートフォリオ値・利用可能現金等を元に発注株数を計算。risk_based / equal / score に対応。
      - 単元株（lot_size）で丸め、1銘柄上限・aggregate cap（available_cash）適用のためスケーリングと端数処理（余剰キャッシュで再配分）を実装。
      - price 欠損（<=0）の銘柄はスキップしログ出力。

- リサーチ / ファクター計算
  - kabusys.research
    - factor_research:
      - calc_momentum / calc_volatility / calc_value: DuckDB の prices_daily / raw_financials テーブルを用いた各ファクター計算を実装（MA200, ATR20, 各種リターン等）。
      - 欠損データ時の None フォールバックや必要行数チェックを実装。
    - feature_exploration:
      - calc_forward_returns: 将来リターン（複数ホライズン）を一括クエリで計算。ホライズン検証（正の整数、最大252日）を実装。
      - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。サンプル不足時は None。
      - factor_summary / rank: 基本統計量とランク付け（同順位は平均ランク）を実装。
    - research パッケージは zscore_normalize（kabusys.data.stats）を再エクスポート。

- AI / ニュース NLP
  - kabusys.ai.news_nlp
    - raw_news を OpenAI API（gpt-4o-mini）でセンチメント評価して ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ計算（前日15:00 JST〜当日08:30 JST の UTC 変換）を実装し、ルックアヘッドバイアスを回避（datetime.today() 等を直接参照しない設計）。
    - 記事集約、1銘柄あたりの文字数/記事数制限（トリム）、最大バッチサイズ（20銘柄）で API コールするバッチ処理を実装。
    - レート制限（429）、ネットワーク断、タイムアウト、5xx を対象とした指数バックオフによるリトライ実装（上限 _MAX_RETRIES）。
    - API レスポンスの検証、スコアの ±1.0 クリップ、取得後は部分的に DELETE→INSERT で ai_scores を置換する安全な更新戦略（部分失敗時に既存スコアを保持）。
    - API キー未指定時のエラーハンドリング（明確な ValueError）。

- ユーティリティ
  - kabusys.utils.process_priority
    - set_process_priority: Windows と POSIX (Linux/macOS/FreeBSD) に対応したプロセス優先度設定。未対応 OS はスキップして警告。
    - set_cpu_affinity: カレントプロセスを最初の N コアに固定する機能を追加（引数検証と例外ハンドリング有り）。
    - 権限不足や未実装例外時には警告を出力して安全にスキップ。

Changed
- コード設計
  - DuckDB と SQLite の併用を前提とした設計に統一（分析は DuckDB、軽量監視は SQLite）。
  - 起動スクリプトでプロセス優先度設定を早期に行うことで実行時の安定性を向上。

Fixed
- 安全性・堅牢性の改善
  - MONITOR_POLL_INTERVAL の不正値（文字列・0・負数）を検出してデフォルトにフォールバックし警告を出力（run_monitoring）。
  - calc_score_weights: 全スコアが 0 の場合に等金額配分へフォールバックして警告を出すように修正。
  - DB/テーブル未存在やデータ不足時にツールがクラッシュしないように OperationalError を捕捉してフォールバックする処理を追加（paper_verification_report など）。
  - calc_position_sizes の aggregate スケーリングアルゴリズムで lot_size 単位の再配分・上限チェックを行い、現金不足時の安全弁を実装。

Notes / その他
- 実装上の留意点（今後の改善メモ）
  - position_sizing の価格欠損（price == 0）の場合、前日終値や別のフォールバック価格を使う改善がコメントとして残されている。
  - .env パーサは多くのケースに対応しているが、完全なシェルの展開互換を目指す場合は更なる拡張が必要。
  - ai/news_nlp の OpenAI 呼び出し部は堅牢なバリデーション・リトライを備えるが、実運用ではログ集約・監視メトリクス・課金対策（呼び出し頻度の抑制）を検討すること。

以上。コードベースの静的解析から推測して記述したCHANGELOGです。必要であれば各項目をさらに詳述（関連ファイル/関数名のリンク付けやコード抜粋）できます。