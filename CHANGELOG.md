# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースの内容から推測して作成したもので、実装上の注記や既知の制約（TODO 相当）も併記しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 初期リリース
リリース日: Unreleased

### 追加 (Added)
- 全体
  - KabuSys 初期実装を追加。パッケージメタ情報にバージョン __version__ = "0.1.0" を設定。
- 実行・監視スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite （デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory を用いて実行時にブローカークライアントを生成。
    - ExecutionEngine を別スレッドで起動し、data/stop_requested.flag の検出で安全に停止可能。
    - 実行中の PID を data/execution.pid に書き込む仕組み（pid_file 経由）。
    - デフォルトでプロセス優先度を "high" に設定。
  - run_monitoring.py: SystemMonitor（監視ループ）を起動するエントリポイントを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境にかかわらず本番用 sqlite_path を使用（monitoring 用テーブルを初期化）。
    - data/stop_requested.flag による停止検知をサポート。
    - 起動時にプロセス優先度を "high" に設定。
- 設定・ユーティリティ
  - config.py: 環境変数 / .env の読み込みと Settings クラスを実装。
    - プロジェクトルート自動検出 (.git または pyproject.toml を探索) に基づき .env, .env.local を自動読み込み（無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を用意）。
    - .env ファイルのパースはクォート・エスケープ・コメント処理に対応。
    - Settings クラスで多数の設定プロパティを提供（J-Quants / kabu API / DB パス / ペーパートレード設定 / 監視しきい値 / システム env/log 等）。
    - 環境値検証（有効値チェック）を実装。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - 各設定項目の説明・デフォルト提示・シークレットマスク表示などを行い .env を生成。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在確認（PyYAML がない場合は YAML 検証をスキップ）。
    - --strict オプションで警告を失敗扱いにできる。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。
    - stdout（StreamHandler）と日次ローテーションファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ自動作成、LOG_LEVEL / LOG_DIR の環境変数対応、既存ハンドラのクリアに対応。
  - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）に対応し、nice / Windows 優先度定数を利用。
    - CPU affinity を最初の N コアに固定する関数を提供。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py: 候補選定と重み計算関数を追加。
    - select_candidates: スコア降順 + signal_rank によるタイブレーク。
    - calc_equal_weights / calc_score_weights: 等配分とスコア加重。全スコアが 0 の場合は等配分にフォールバック（警告）。
  - portfolio/risk_adjustment.py: セクター集中制限・レジーム乗数を追加。
    - apply_sector_cap: 既存保有に基づきセクターごとのエクスポージャを算出し、上限超過セクターの新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: "bull"/"neutral"/"bear" に対する投下資金乗数を返す（未定義レジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py: 株数決定ロジックを追加。
    - allocation_method: "risk_based", "equal", "score" に対応。
    - 単元株（lot_size）で丸め、最大ポジション比率・利用可能現金（aggregate cap）に応じたスケールダウンロジック、cost_buffer を考慮した保守的見積もりを実装。
    - risk_based 時は stop_loss_pct, risk_pct に基づく算出。
    - スケーリング時の残差配分アルゴリズム（fractional remainder に基づく lot 単位での再配分）を実装。
    - 実装中の将来的拡張点: 銘柄別 lot_size のサポート（TODO コメントあり）。
- リサーチ
  - research/factor_research.py: ファクター計算フレームワークを追加（モメンタム等の定義と calc_momentum の骨組み）。
    - DuckDB 接続を受け prices_daily / raw_financials を用いてファクター計算を行う設計。
    - モメンタム指標（1M/3M/6M、MA200 乖離等）やボラティリティ等の計算方針を文書化。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成ツールを追加。
    - PAPER_TRADING_SQLITE_PATH 環境変数／--db オプションで DB 指定可能。
    - システム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計して PASS/FAIL 判定（閾値はファイル内で定義）。
    - 日付フィルタ（--from / --to）に対応。
  - tools パッケージを追加（__init__.py）。

### 変更 (Changed)
- 該当なし（初期リリースのため新規実装中心）。

### 修正 (Fixed)
- 該当なし（初期リリースのため新規実装中心）。

### 注意点 / 既知の制約 (Notes / Known issues)
- config.py の自動 .env 読み込みはプロジェクトルート検出に依存するため、配布後や別ディレクトリからの実行時に検出できない場合は自動読み込みがスキップされる。
- position_sizing.calc_position_sizes:
  - price_map（open_prices）の欠損時に price=0.0 として扱うとエクスポージャが過小見積りされる懸念があり、将来的に前日終値等のフォールバック価格を導入する旨の TODO が記載されている。
- research/factor_research.py:
  - ファクター計算の方針および calc_momentum の冒頭実装が含まれているが、ファイル末尾が途切れている（コードスニペットの都合）。実運用前に完全実装とテストが必要。
- ログディレクトリ作成に失敗した場合はファイルハンドラをスキップして stdout のみでログ出力する設計。
- process_priority.set_process_priority/set_cpu_affinity は権限不足やプラットフォーム未対応時に警告を出してスキップする（安全設計）。
- validate_config.py は PyYAML 未インストール時に YAML 内容検証をスキップする（警告を表示）。

### セキュリティ (Security)
- .env ファイルを生成する CLI は生成時に「.env を絶対に Git にコミットしない」注意書きを出力。
- シークレット項目（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / LINE token 等）は対話ウィザードでマスク表示を行う。

---

（注）本 CHANGELOG は提供されたソースコードの内容に基づいて推測して作成したものであり、実際のコミット履歴や変更履歴とは異なる可能性があります。リリース日や将来の改修については、実際のバージョン管理履歴（git など）に基づいて更新してください。