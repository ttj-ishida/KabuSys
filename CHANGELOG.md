CHANGELOG
=========
（このファイルは Keep a Changelog 仕様に準拠しています。すべての重要な変更点を日付順に記録してください。）

Unreleased
----------
- なし（現時点ではリリース済みの状態のみを記載しています）

0.1.0 - 2026-04-13
-----------------
Added
- 全体
  - 初回公開版。日本株自動売買フレームワーク「KabuSys」のコア機能を実装。
  - パッケージバージョンを __version__ = "0.1.0" として設定（src/kabusys/__init__.py）。

- 設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能を導入（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env パーサを実装（コメント、export プレフィックス、クォート内のエスケープ対応等）。
  - 読み込み順序: OS環境変数 > .env.local > .env（OS環境変数は保護され上書きされない）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを実装し、環境変数から各種設定値（DBパス、APIトークン、閾値、環境名など）を提供。
  - 環境値の検証を追加（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。

- 実行・デーモン管理ユーティリティ
  - プロセス優先度（および CPU affinity）設定ユーティリティを実装（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX（Linux/Mac/FreeBSD）に対応。権限不足や未対応 OS の場合は警告を出してスキップ。
  - 実行エントリ:
    - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
      - set_process_priority("high") を起動時に適用。
      - Paper Trading 環境（KABUSYS_ENV=paper_trading）では brokerFactory が MockBrokerClient を選択し、paper_trading 用 SQLite（data/paper_trading.db デフォルト）を使用して本番 DB と分離。
      - 依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を組み立て実行。
      - init_monitoring_db を呼び出して監視テーブルの存在を冪等に保証。
    - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
      - MONITOR_POLL_INTERVAL 環境変数でポーリング周期を上書き可能（デフォルト 60 秒）。不正値（0 以下・非数）はデフォルト値にフォールバックし警告を出す。
      - 監視は環境にかかわらず本番 sqlite_path を使用する旨を明示。
      - ループ内で monitor.check_once() を呼び例外をハンドル、KeyboardInterrupt でのグレースフルな終了処理を実装。
      - DuckDB/SQLite の接続クローズを finally ブロックで保証。

- モニタリング / DB 初期化
  - 監視用 DB 初期化イニシャライザ（init_monitoring_db）を呼び出すことで監視テーブルの存在を保証（冪等）。

- ポートフォリオ構築（src/kabusys/portfolio/*）
  - 銘柄選定（select_candidates）: スコア降順・同点は signal_rank 昇順でタイブレーク。
  - 重み計算:
    - 等金額配分 calc_equal_weights。
    - スコア加重 calc_score_weights（全銘柄スコアが0.0なら等金額にフォールバックし警告）。
  - セクター制限 apply_sector_cap:
    - 既存保有のセクター別時価を計算して上限（max_sector_pct）を超えるセクターの新規候補を除外（"unknown" セクターは制限適用外）。
    - 当日売却予定銘柄を露出計算から除外可能。
  - レジーム乗数 calc_regime_multiplier:
    - "bull"=1.0, "neutral"=0.7, "bear"=0.3。未知のレジームは警告を出して 1.0 にフォールバック。
  - ポジションサイズ calc_position_sizes:
    - risk_based / equal / score の割当方式をサポート。
    - lot_size（単元）考慮の丸め、max_position_pct による per-stock 上限、available_cash による aggregate 上限のスケーリング処理を実装。
    - cost_buffer を用いた保守的コスト見積りと、残余キャッシュを使った lot 単位での追加配分ロジックを実装。

- リサーチ（src/kabusys/research/*）
  - ファクター計算（factor_research）
    - モメンタム（1M/3M/6M リターン、MA200乖離率）
    - ボラティリティ（20日 ATR、ATR 比率、20日平均売買代金、出来高比率）
    - バリュー（PER, ROE を raw_financials と prices_daily 組合せで算出）
    - DuckDB を利用した SQL ベースの計算を実装（prices_daily / raw_financials を参照）。
  - 特徴量探索（feature_exploration）
    - 将来リターン calc_forward_returns（任意ホライズン、入力検証あり）
    - IC（スピアマン相関）計算 calc_ic、安定したランク関数 rank、統計サマリー factor_summary を提供。
  - すべて外部 API に依存せず、DuckDB のみで完結する設計。

- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news を OpenAI（gpt-4o-mini）でセンチメント解析し、銘柄ごとの ai_scores に書き込む処理を実装。
  - 処理フロー:
    - 対象時間ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を計算する calc_news_window。
    - 記事を銘柄ごとに集約（最大記事数・文字数でトリム）。
    - 最大 20 銘柄ずつのバッチ送信、レスポンス検証、スコアを ±1.0 にクリップ。
    - 429 / ネットワーク / タイムアウト / 5xx については指数バックオフでリトライ（上限あり）。
    - APIキー未設定時に ValueError を送出。
    - 書き込みは部分失敗を考慮して対象コードでの置換操作（DELETE→INSERT）を想定しフェイルセーフに配慮。
  - トークン肥大化対策や JSON レスポンス厳密検証などを実装。

- ツール（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading 検証レポート生成スクリプトを追加。
  - 指標:
    - 稼働率（稼働率閾値 99.0%）
    - 注文成功率（閾値 90%）、送信率（閾値 95%）
    - P95 レイテンシ（閾値 200 ms）
  - 日付フィルタ (--from/--to) をサポートし、P95 を含む各種集計を SQLite から取得して標準出力に整形して出力。
  - テーブルが存在しない場合のフォールバック（OperationalError ハンドリング）を実装。

Changed
- 環境変数の取り扱い
  - .env の読み込み挙動は OS 環境変数を尊重するよう変更（明示的に protected set を持つ）。
  - .env の export KEY=val 形式やクォート、エスケープ、インラインコメントの取り扱いを強化。

- DB レイアウト / 運用
  - Paper Trading 環境用に SQLite DB を完全に分離（settings.paper_sqlite_path を利用）。運用時に本番データと混在しない設計。

Fixed
- 環境・設定の堅牢化
  - MONITOR_POLL_INTERVAL に不正な値が設定された場合、time.sleep で ValueError を起こさないよう 0 以下や非数をデフォルト値にフォールバックし警告を出す処理を追加（src/kabusys/run_monitoring.py）。
  - .env パーサーでのクォート内エスケープや '#' コメント判定を改善し誤読を防止。
  - calc_score_weights: 全スコアが 0.0 の場合にゼロ除算を回避し等金額配分にフォールバック。

Security
- OpenAI API キーの扱い
  - AI モジュールは api_key 引数または環境変数 OPENAI_API_KEY の明示的指定を必須とし、未設定時はエラーにして誤動作を防止。

Notes / Known issues
- news_nlp の実装は外部 API（OpenAI）依存のため、API 料金・レート制限に注意が必要。リトライロジックはあるが過度な再試行はコスト増につながる。
- apply_sector_cap は price_map に 0.0 が含まれるとエクスポージャーが過少見積りになる可能性がある旨の TODO コメントあり（将来的に価格フォールバックを追加予定）。
- position_sizing の lot_size は現状グローバル固定（既定 100）。将来的には銘柄別単元対応の拡張計画あり。
- calc_regime_multiplier で未知レジームは 1.0 にフォールバックするが、運用ルールに応じた見直しを検討推奨。

移行ガイド
- .env 自動読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading 環境では SQLite パスや PAPER_FILL_MODE 等の設定を確認し、本番 DB を誤って上書きしないよう注意してください。

作者注
- 本 CHANGELOG はソースコードからの実装意図・挙動を推測して作成しています。細かな挙動や追加の変更履歴は実際のコミットログやリリースノートと照合してください。