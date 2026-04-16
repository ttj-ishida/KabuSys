Keep a Changelog
=================

すべての変更は慣例に従い日付順に記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

[Unreleased]
-----------

- （なし）

[0.1.0] - 2026-04-16
--------------------

Added
- 初回リリース: 日本株自動売買システムの基本コンポーネントを追加。
  - ポートフォリオ構成モジュール（メインロジック）を追加（kabusys/portfolio）
    - 候補選定と重み算出: select_candidates, calc_equal_weights, calc_score_weights（portfolio_builder.py）
    - セクター集中制限・レジーム乗数: apply_sector_cap, calc_regime_multiplier（risk_adjustment.py）
    - ポジションサイズ算出（単元株丸め・リスクベース／等配分／スコア配分・集計制約）: calc_position_sizes（position_sizing.py）
  - リサーチ用モジュール（kabusys/research）
    - ファクター計算: calc_momentum, calc_volatility, calc_value（factor_research.py）
    - 特徴量探索: 将来リターン算出(calc_forward_returns)、IC（calc_ic）、統計サマリ（factor_summary）、ランク変換（rank）（feature_exploration.py）
    - z-score 正規化ユーティリティをエクスポート（kabusys/research/__init__.py）
  - AI ニュース NLP スコアリング（kabusys/ai/news_nlp.py）
    - OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析のための処理フローを実装（バッチ処理・トリミング・API 再試行・レスポンス検証・スコアクリッピングなど）
    - 指定日向けのニュースウィンドウ計算ユーティリティを実装（calc_news_window）
  - 実行／監視用の起動スクリプトを追加
    - 実行エンジン起動スクリプト（run_execution.py）
      - 環境が paper_trading の場合は MockBroker と専用 DB（data/paper_trading.db）を利用して本番 DB と完全分離
      - 停止フラグ（data/stop_requested.flag）検知で安全停止、pid ファイル管理、スレッドでの実行
    - 監視ループ起動スクリプト（run_monitoring.py）
      - プロセス優先度設定、DB 初期化、SystemMonitor のポーリングループ化（MONITOR_POLL_INTERVAL で間隔を上書き可能）
      - 監視は環境にかかわらず本番 sqlite_path を参照（設計上の意図）
  - 設定管理（kabusys/config.py）
    - .env / .env.local 自動ロード（OS 環境変数保護・override 挙動の区別、.git/pyproject.toml を基準にプロジェクトルート自動探索）
    - .env 行パーサ強化（export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント処理）
    - Settings クラス: 各種環境変数アクセスプロパティ（DB パス・paper_trading 用パス・監視閾値・env 判定など）を提供し、値検証を実施
  - ユーティリティ（kabusys/utils/process_priority.py）
    - set_process_priority / set_cpu_affinity を実装し、Windows と POSIX の差分を吸収
    - 権限不足や未対応プラットフォームに対する安全ハンドリングを実装
  - ツール（kabusys/tools/paper_verification_report.py）
    - Paper Trading 用検証レポート生成スクリプトを追加（稼働率・注文成功率・送信率・P95 レイテンシ等の算出、閾値による PASS/FAIL 判定）
    - P95 計算、日付フィルタ、DB 存在チェック、出力フォーマットを実装
  - パッケージメタ情報（kabusys/__init__.py）にバージョンを設定（0.1.0）

Changed
- 監視・実行起動ロジックの設計決定を明確化
  - run_monitoring: MONITOR_POLL_INTERVAL の環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
  - run_execution: paper_trading 環境時に専用 SQLite（paper_sqlite_path）を使用して発注ログ等を本番と分離。

Fixed / Robustness improvements
- .env パーサで様々な実用ケースに対応（引用符内のエスケープ・export の扱い・インラインコメントの取り扱い）して、テストや運用時の誤設定に強くした（config.py）。
- calc_score_weights が全スコア 0 の場合に等金額配分へフォールバックし警告を出すようにして、ゼロ除算や不正な重み配分を回避（portfolio/portfolio_builder.py）。
- position sizing の丸め処理（lot_size 単位）・per-stock 上限・aggregate cap（利用可能現金でスケールダウン）を厳密化。手数料等を考慮する cost_buffer を導入（portfolio/position_sizing.py）。
- ファクター計算（momentum, volatility, value）でデータ不足時は None を返すなど NULL 安全性を強化（research/factor_research.py）。
- feature_exploration の rank / calc_ic 実装で ties（同順位）や浮動小数の丸め誤差に配慮し、スピアマン相関の安定計算を行う（research/feature_exploration.py）。
- process_priority の権限エラーや未対応環境での失敗を警告に留めて処理継続するようにした（utils/process_priority.py）。
- news_nlp: API 呼び出しに対して 429 / ネットワーク断 / タイムアウト / 5xx を想定した指数バックオフとリトライ方針を組み込み、レスポンス検証（JSON 構造・型・既知銘柄チェック）・スコアクリップを導入して不正データ流入を防止（ai/news_nlp.py）。
- run_execution / run_monitoring: 停止フラグ（data/stop_requested.flag）検知で安全に停止する処理を追加。

Documentation / Messages
- 各モジュールに詳しい docstring と設計方針コメントを追加。内部アルゴリズムや制約（データ不足時の挙動、想定単元株数、注記など）を明記。

Known issues / Notes
- news_nlp.py はニュース記事の集約→API 呼び出し→DB 書き込みまでの処理フローを実装していますが、提供されたコードスニペット内で記事集約フェーズ以降の一部が切れている箇所があります。実運用時は score_news の最終的な記事フェッチ／バッチ送信／DB 更新の完全実装を確認してください。
- 一部の TODO コメント（position_sizing の銘柄別 lot_size 対応、apply_sector_cap の価格欠損時のフォールバック等）が残っています。今後の改善候補です。

Security
- （なし）

References (主要ファイル)
- run_monitoring.py, run_execution.py
- config.py
- portfolio/portfolio_builder.py, portfolio/position_sizing.py, portfolio/risk_adjustment.py
- research/factor_research.py, research/feature_exploration.py
- ai/news_nlp.py
- utils/process_priority.py
- tools/paper_verification_report.py
- __init__.py (バージョン)

----

訳注: 本 CHANGELOG は提示されたコードベースから推測して作成しています。実際のコミット履歴や変更差分に基づくものではないため、細部は実際の履歴と異なる可能性があります。