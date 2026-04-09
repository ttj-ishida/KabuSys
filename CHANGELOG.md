# CHANGELOG

すべての重要な変更はこのファイルに記録します。本プロジェクトは Keep a Changelog の慣例に従います。
安定したリリースのバージョン番号は semver を使用します。

## [0.1.0] - 2026-04-09
初回リリース。日本株自動売買フレームワークの基礎機能を実装しました。

### 追加
- 基本パッケージ情報
  - パッケージバージョンを定義（kabusys.__version__ = "0.1.0"）。公開 API 用の __all__ を設定。 (src/kabusys/__init__.py)

- 環境変数 / 設定管理
  - .env ファイルまたは OS 環境変数から設定を読み込む Settings モジュールを実装。必須設定は未設定時に ValueError を送出。 (src/kabusys/config.py)
  - .env 自動読み込み機能をプロジェクトルート (.git または pyproject.toml を起点) から行う実装を追加（CWD 非依存）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。 (src/kabusys/config.py)
  - .env パーサーは export 構文、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント等に対応する堅牢な実装。 (src/kabusys/config.py)
  - 各種設定プロパティを提供（API トークン、DB パス、paper trading 設定、監視閾値、環境 / ログレベル等）および値検証（PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等）。 (src/kabusys/config.py)

- ポートフォリオ構築（純関数群）
  - 候補選定: シグナルをスコア降順＋タイブレークでソートして上位 N を選択する select_candidates を実装。 (src/kabusys/portfolio/portfolio_builder.py)
  - 重み計算:
    - 等金額配分 calc_equal_weights を実装。
    - スコア加重配分 calc_score_weights を実装（全スコアが 0 の場合は等配分にフォールバックして警告）。 (src/kabusys/portfolio/portfolio_builder.py)

- リスク調整
  - セクター集中制限 apply_sector_cap を実装。既存保有のセクター比率が閾値を超える場合に当該セクターの新規候補を除外（unknown セクターは無視）。 (src/kabusys/portfolio/risk_adjustment.py)
  - 市場レジームに基づく資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマップと未知レジームのフォールバック）。 (src/kabusys/portfolio/risk_adjustment.py)

- ポジションサイジング
  - calc_position_sizes を実装。以下の機能をサポート:
    - allocation_method: "risk_based", "equal", "score"
    - リスクベースでの株数算出、損切り率・許容リスク率の反映
    - 単元株（lot_size）丸め、1 銘柄上限・ポートフォリオ総合上限の適用
    - 手数料・スリッページを考慮した cost_buffer、利用可能現金に応じたスケーリング（aggregate cap）
    - スケールダウン時の端数処理（lot_size 単位で残差順に再配分）
  - 将来的な拡張点（銘柄別 lot_size の導入）をコメントで明示。 (src/kabusys/portfolio/position_sizing.py)

- リサーチ / ファクター計算
  - モメンタム、ボラティリティ、バリュー等のファクター計算関数を実装（DuckDB 接続を受け取り SQL＋Python で計算）。各関数は prices_daily / raw_financials テーブルのみ参照する設計。 (src/kabusys/research/factor_research.py)
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離
    - calc_volatility: 20日 ATR、ATR 比率、平均売買代金、出来高比率
    - calc_value: PER（EPS が 0 の場合は None）および ROE（raw_financials から最新レコードを取得）
  - 研究用ユーティリティ:
    - 将来リターン一括取得 calc_forward_returns（可変ホライズン、安全性チェック）
    - IC（Spearman の ρ）計算 calc_ic とランク付け rank（同順位は平均ランク）
    - 統計サマリー factor_summary（count/mean/std/min/max/median） (src/kabusys/research/feature_exploration.py)
  - research パッケージのエクスポートを整理。 (src/kabusys/research/__init__.py)

- AI（LLM）連携
  - ニュース NLP:
    - raw_news を集約して OpenAI（gpt-4o-mini）で銘柄別センチメントを計算し ai_scores テーブルに書き込む score_news を実装。記事ウィンドウの算出、チャンク／バッチ処理、最大文字数/記事数のトリム、レスポンス検証、クリッピング、部分書き換え（DELETE→INSERT）を行う。 (src/kabusys/ai/news_nlp.py)
    - OpenAI 呼び出しのリトライ（429・接続エラー・タイムアウト・5xx に対する指数バックオフ）、JSON Mode を利用したレスポンス検証、部分失敗時のフェイルセーフ動作を実装。
    - テストを容易にするため API 呼び出し関数が差し替え可能（モック可）。 (src/kabusys/ai/news_nlp.py)
  - レジーム判定:
    - ETF(1321) の MA200 乖離とマクロニュース LLM スコアを合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルに冪等書き込みする score_regime を実装。LLM 呼び出し失敗時は macro_sentiment=0.0 でフォールバック。 (src/kabusys/ai/regime_detector.py)
    - news_nlp の calc_news_window を流用してニュースウィンドウを一致させる設計。 (src/kabusys/ai/regime_detector.py)
  - ai パッケージのエクスポートを整理。 (src/kabusys/ai/__init__.py)

- 監視ログ永続化
  - SQLite ベースの監視ログ層 init_monitoring_db を実装。system_status / trade_logs / positions / risk_logs などのテーブルとインデックスを作成するスクリプトを提供（冪等）。 (src/kabusys/monitoring/monitoring_db.py)

### 変更
- なし（初回リリースのため「追加」が中心）

### 修正 / 安全性・堅牢性強化
- .env 読み込みでファイルアクセスエラー時に警告を出して処理継続する安全な実装。 (src/kabusys/config.py)
- ファクター／リサーチ関数はルックアヘッドバイアス対策として計算時に target_date を厳密に扱うよう設計。 (src/kabusys/research/*)
- LLM 呼び出しについては:
  - リトライの範囲を明確化（429/ネットワーク/タイムアウト/5xx）し、上限超過時はログ出力してスキップするフェイルセーフを採用。 (src/kabusys/ai/*)
  - レスポンス検証を厳密化（JSON 抽出、キー/型チェック、未知コードの無視、数値チェック、クリッピング）。 (src/kabusys/ai/news_nlp.py)
- DB 書込みはトランザクションを使い、例外時はロールバックを試みる実装（失敗時は上位へ伝播）。 (src/kabusys/ai/*)

### ドキュメント / コメント
- 各モジュールに処理フロー、設計方針、制約、将来の拡張案を詳細な docstring とコメントで記載（研究用関数は外部依存を避ける設計を明文化）。 (各ファイル全般)

### 既知の制限 / TODO
- position_sizing の lot_size は現状全銘柄共通（将来的に銘柄別 lot_map を想定）。 (src/kabusys/portfolio/position_sizing.py)
- apply_sector_cap は price の欠損時にエクスポージャーを過少に見積もる可能性がある旨を TODO コメントで記載。 (src/kabusys/portfolio/risk_adjustment.py)
- DuckDB の executemany に空リストを渡せない点に合わせたワークアラウンドを実装（params が空でないことを確認）。 (src/kabusys/ai/news_nlp.py)
- monitoring_db のテーブル定義は初期部分まで実装（ファイル断片のため残りは実装済みである想定）。

---

今後のリリースでは、テストカバレッジ、エラーケースのより詳細なハンドリング、DB スキーマの確定、外部 API のモック化検証、銘柄別単元対応などの改善を予定しています。