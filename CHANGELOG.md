Keep a Changelog
================

すべての重要な変更点をバージョン別に記録します。  
本ファイルは Keep a Changelog の形式に準拠しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-12
-----------------

Added
- パッケージの初期リリースを追加。
  - パッケージバージョンは kabusys.__version__ = "0.1.0"。
- 起動スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - 環境変数 KABUSYS_ENV により paper_trading を判定し、paper_trading 時は MockBrokerClient を使用可能（BrokerClientFactoryに依存）。
    - paper_trading 用 SQLite DB を分離（data/paper_trading.db をデフォルト）。
    - ExecutionEngine の組み立て（OrderRepository, OrderManager, RiskManager, Reconciler 等）とセッション実行を行う。
  - 監視ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - 監視ループ内での例外を捕捉してログに記録し、次のポーリングへ継続するフェイルセーフを導入。
- 設定管理
  - 環境変数 / .env 自動ロード機能を実装（src/kabusys/config.py）。
    - プロジェクトルート検出（.git または pyproject.toml を探索）により .env / .env.local を自動読み込み。
    - OS 環境変数の保護（既存の環境変数を上書きしない、.env.local は上書き可）。
    - 詳細な .env パース（export 形式、クォート内のエスケープ、インラインコメントの扱い等）に対応。
    - 各種設定プロパティを提供（DB パス、PaperTrading モード、監視閾値、PID/kill フラグパス、環境判定メソッド等）と入力値検証。
- ポートフォリオ構築ライブラリ（src/kabusys/portfolio/*）
  - 銘柄選定と重み付け（select_candidates、calc_equal_weights、calc_score_weights）。
    - スコア降順ソート、同点時のタイブレークロジックを実装。
    - スコアが全てゼロの場合は等配分にフォールバック（警告ログ）。
  - セクター集中制限とレジーム乗数（apply_sector_cap、calc_regime_multiplier）。
    - 既存保有のセクター別エクスポージャ計算（売却予定銘柄の除外対応）。
    - レジームに応じた投下資金乗数（bull/neutral/bear）を実装。未知レジームはフォールバック。
  - 位置決定（calc_position_sizes）
    - risk_based / equal / score の allocation_method をサポート。
    - 単元株（lot_size）丸め、銘柄毎最大ポジション上限、合計投下資金に応じたスケーリング（aggregate cap）。
    - cost_buffer を用いた保守的コスト見積、スケールダウン時の残差ロジック（端数を lot_size 単位で再配分）を実装。
- 研究 / ファクター計算（src/kabusys/research/*）
  - ファクター計算モジュールを追加。
    - calc_momentum: 1M/3M/6M リターン・MA200乖離率（データ不足時は None）。
    - calc_volatility: 20日 ATR、相対ATR（atr_pct）、20日平均売買代金、出来高比率。
    - calc_value: raw_financials と価格から PER/ROE を計算（過去データの最新レコード参照）。
  - 特徴量探索ユーティリティを追加。
    - calc_forward_returns: 指定ホライズンに対する将来リターン（複数ホライズン一括取得）。
    - calc_ic: スピアマンランク相関による IC 計算（有効レコードが 3 件未満なら None）。
    - rank / factor_summary: ランキングと基本統計量（count/mean/std/min/max/median）。
  - DuckDB 接続を受け取る設計で、prices_daily / raw_financials テーブルのみ参照する（本番 API に依存しない）。
- AI ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
  - raw_news を OpenAI（gpt-4o-mini）でセンチメント判定し、ai_scores テーブルへ書き込むロジックを実装。
  - 機能:
    - タイムウィンドウ計算（JST 基準 → UTC 変換）。
    - 銘柄ごとの記事集約（1 銘柄あたり記事数・文字数の上限トリム）。
    - 最大バッチサイズでの API バッチ送信（デフォルト 20 銘柄）。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフのリトライ。
    - レスポンスの厳密な JSON バリデーション、スコアの ±1.0 クリップ。
    - 成功した銘柄のみを対象に部分的に ai_scores を置換（部分失敗に強い操作）。
- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - CLI オプションで期間指定（--from / --to）と DB パス指定（--db）。
    - 指標: 稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数など。
    - 判定基準（PASS/FAIL）と閾値を定義（稼働率 99% 等）。
    - DB にテーブルが存在しない場合にも安全に動作するフォールバック処理を実装。
- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX (Linux/Mac/FreeBSD) の違いを吸収。
    - set_process_priority(level) により nice / priority 設定（権限不足時は警告でスキップ）。
    - set_cpu_affinity(cpu_count) により最初の N コアにプロセスを固定（権限不足時は警告でスキップ）。

Changed
- 環境読み込みの優先順位を明確化（OS 環境変数 > .env.local > .env）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- 監視（run_monitoring）の挙動:
  - 監視は常に Settings.sqlite_path（本番の monitoring DB）を使用するように明記。紙トレード環境でも監視 DB は分離しない設計。
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）に対しては警告ログを出し、デフォルトにフォールバックする安全措置を追加。
- ExecutionEngine の DB 接続:
  - paper_trading 環境時は専用 SQLite を使用して本番 DB と完全分離する挙動を採用（settings.paper_sqlite_path を使用）。
- DB 初期化:
  - init_monitoring_db を起動前に呼び出して監視テーブルの存在を保証（冪等性を考慮）。
- 設定プロパティでの入力検証を強化:
  - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の不正値に対する ValueError を追加。
  - 各種閾値（CPU/MEM/DISK）やパス類はプロパティ経由で取得し、デフォルト値を文書化。

Fixed
- 例外耐性の強化:
  - 監視ループ内で monitor.check_once() が例外を投げてもループを停止せずログに記録して継続するように修正。
  - .env ファイル読み込みでファイルアクセス失敗時に警告を出してスキップするよう改善。
- position_sizing のスケーリング処理において、
  - 合計コストが利用可能現金を超えた際のスケールダウンと残余キャッシュを使った端数配分を実装し、投下資金上限を守るよう改善。
- research モジュールの SQL 実行で、
  - データ不足を考慮した NULL ハンドリング（COUNT による判定）を追加し、欠損時に None を返すことで downstream の壊れを防止。
- ai/news_nlp:
  - API キー未設定時に明確な ValueError を送出するように変更（早期エラー検出）。

Deprecated
- （なし）

Removed
- （なし）

Security
- OpenAI API キーは関数引数または環境変数 OPENAI_API_KEY から解決。未設定時はエラーを出して処理を停止する（キー漏洩防止のためログにキーは出力しない実装を想定）。

Notes / TODO（コード内コメントより抜粋）
- position_sizing:
  - lot_size を将来的に銘柄毎に拡張する検討（stocks マスタへの lot_size 追加）。
  - price 欠損時のフォールバック価格（前日終値や取得原価など）の採用検討。
- risk_adjustment:
  - "unknown" セクターはセクターキャップを適用しない設計。必要に応じて処理見直しの余地あり。
- ai/news_nlp:
  - JSON Mode のレスポンス検証や部分置換戦略により部分失敗からの影響を最小化。429 などのリトライ挙動はパラメータ調整が可能。
- general:
  - DuckDB を用いた分析パイプラインは外部 API に依存せず再現性の高い設計。将来的な性能チューニングや並列化の余地あり。

もし別バージョンや過去の差分（例: 0.0.x → 0.1.0 の差分）としての表現が必要であれば、ソース管理履歴やリリース予定日を教えてください。コードから推測できた範囲でさらに細かく項目を分けて記載できます。