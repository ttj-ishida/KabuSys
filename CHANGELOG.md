# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

※ このリリースはソースコードから推測して作成した変更点をまとめたものです。

## [0.1.0] - 初回リリース (推定)
リリース日: 未設定

### 追加 (Added)
- 全体
  - パッケージの初期公開相当の機能群を追加。
  - __version__ を "0.1.0" に設定 (src/kabusys/__init__.py)。

- 実行スクリプト
  - run_monitoring 起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - SystemMonitor のポーリングループを起動。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視用 DB は KABUSYS_ENV にかかわらず本番 sqlite_path を使用。
    - プロセス優先度を起動時に High に設定。
  - run_execution 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - ExecutionEngine を組み立てて実行。
    - KABUSYS_ENV=paper_trading の際は専用の paper_trading DB（data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - 実行中はプロセス優先度を High に設定。

- 設定管理
  - Settings クラスを追加（src/kabusys/config.py）。
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml ベース）。
    - .env と .env.local の読み込み順序（OS 環境変数を保護）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` で自動ロードを無効化可能。
    - .env の行パーサを実装:
      - `export KEY=val` 形式対応。
      - シングル/ダブルクォート内でのバックスラッシュエスケープ対応。
      - クォートなし時のインラインコメント取り扱い。
    - 必須環境変数取得時のエラー報告 (`_require`)。
    - 多数のプロパティを提供（J-Quants, kabu API, LINE, DB パス, PID/KILL フラグ, 閾値パラメータ, 環境判定等）。
    - `PAPER_FILL_MODE` の検証（有効値: instant/partial/never/reject）。
    - `KABUSYS_ENV` / `LOG_LEVEL` のバリデーション。

- モニタリング／ツール
  - 監視 DB 初期化ユーティリティを参照して起動時にテーブル存在を保証（init_monitoring_db を使用）。
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - CLI から期間指定 (--from / --to / --db) でレポート出力可能。
    - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数等を算出。
    - P95 計算、日付フィルタ構築、耐障害的な SQL 実行（テーブルが無ければデフォルト値で継続）。
    - 判定閾値を定義して PASS/FAIL を出力。

- ポートフォリオ構築関連（純関数群）
  - 銘柄選定と重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順＋signal_rank でタイブレーク。
    - calc_equal_weights / calc_score_weights（スコア合計が 0 の場合は等金額にフォールバック）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有を基にセクター上限を判定し、新規候補を除外（"unknown" セクターは適用しない）。
    - calc_regime_multiplier: market regime に応じた乗数（bull/neutral/bear）を返却、未知のレジームは警告の上で 1.0 にフォールバック。
  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: risk_based / equal / score の配分方式をサポート。
    - 単元株（lot_size）丸め、max_position_pct 上限、aggregate cap によるスケーリング、cost_buffer による保守的コスト見積もり、残差処理による追加配分ロジックを実装。

- 研究（research）モジュール
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB の prices_daily / raw_financials を利用し、各種ウィンドウ処理／欠損処理を考慮。
    - 各関数は (date, code) 単位の辞書リストを返す設計。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns（任意ホライズン）、calc_ic（スピアマンランク相関）、rank、factor_summary（count/mean/std/min/max/median）等を実装。
    - 標準ライブラリのみで実装。入力検証あり（horizons の値範囲等）。
  - research パッケージのエクスポート設定を追加（src/kabusys/research/__init__.py）。

- AI ニュース NLP（部分実装）
  - ニュース記事を OpenAI（gpt-4o-mini）でセンチメントスコア化して ai_scores に書き込む処理を追加（src/kabusys/ai/news_nlp.py）。
    - ニュースウィンドウ計算（JST → UTC 変換）関数 calc_news_window。
    - バッチサイズ、チャンク処理、スコアクリッピング、リトライ（429/ネットワーク/5xx）方針、入力トリミング（記事数・文字数制限）、レスポンス検証、部分成功時のテーブル更新戦略を設計。
    - OpenAI クライアントを使った score_news エントリを追加（API キー検証を行う）。
    - （注）ファイルは途中で切れているが、基本的な設計と多数の安全弁が組み込まれている。

- ユーティリティ
  - プロセス優先度 / CPU affinity 機能を追加（src/kabusys/utils/process_priority.py）。
    - set_process_priority(level): Windows / POSIX (Linux, Darwin, FreeBSD) に対応。アクセス拒否や未サポート環境では警告を出してスキップ。
    - set_cpu_affinity(cpu_count): 最初の N コアにプロセスをピンニングする関数（引数検証あり）。
  - package exports: portfolio / research / utils の __init__ で主要関数を公開。

### 変更 (Changed)
- DB 接続と初期化の振る舞いを明確化
  - 監視(run_monitoring) は環境にかかわらず本番 sqlite_path を使う挙動が明記されている。
  - run_execution は paper_trading 環境時に paper_sqlite_path を使用するよう分岐（本番 DB と分離）。

- ログ設定
  - 実行スクリプト内で logging.basicConfig(level=logging.INFO) によりデフォルトログレベルを INFO に設定。

### 修正 (Fixed)
- 環境変数パースの堅牢化
  - .env パーサが空行・コメント・export プレフィックス・クォート内エスケープ・インラインコメントを適切に扱うよう実装。
  - _get_poll_interval() が 0 以下や非整数の値に対してデフォルトにフォールバックするよう修正（time.sleep に渡す不正値対策）。

- 安全性・フォールトトレランス
  - プロセス優先度や CPU affinity の設定で権限不足や未実装 API に対し例外を捕捉して警告を出し、動作継続するように変更。
  - Paper レポートや研究モジュールでテーブルが存在しない場合に OperationalError を捕捉して Graceful にデフォルト値を返す実装。

### 非互換性 / 注意点 (Breaking Changes / Notes)
- Settings の自動 .env ロードはデフォルトで有効（CWD ではなくパッケージ位置からプロジェクトルート検出を行う）。テスト等で自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定する必要あり。
- run_monitoring は監視 DB に本番 sqlite_path を使うため、テスト環境で監視ループを直接動かすと本番 DB に書き込む可能性がある。テスト用途では環境変数またはコードでパスを調整することを推奨。
- Paper Trading 実行時は別 DB を使用するが、設定によりパス名が変わるため既存の運用スクリプトとの整合に注意。

### セキュリティ (Security)
- OpenAI API キーは環境変数または引数で渡す設計。キー未指定時は score_news が ValueError を送出して安全に停止。

---

今後の改善候補（コード中の TODO 等より推測）
- position_sizing の lot_size を銘柄別に対応するため stocks マスタに lot_size を持たせる拡張。
- apply_sector_cap の価格欠損時のフォールバック（前日終値や取得原価など）。
- news_nlp のログ／エラー周りの追跡・テスト充実、また OpenAI レスポンスの堅牢な検証ロジックの完成。
- DuckDB の executemany 空パラメータ制約を回避するユーティリティ強化。

--- 

以上。必要であれば、ファイル毎の差分要約やリリースノートの英語版、または将来のリリース候補（Unreleased）ブロックの草案も作成します。どれを優先しますか？