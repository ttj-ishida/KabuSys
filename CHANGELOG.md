# Changelog

すべての注目すべき変更をこのファイルで管理します。本書式は Keep a Changelog に準拠しています。  
日付はコードベースから推測して付与しています。実際のリリース日や内容は必要に応じて調整してください。

## [Unreleased]
- 今後の変更点・予定を記載してください。

---

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買／データ基盤向けのコアライブラリを追加。

### Added
- パッケージ初期化
  - kabusys パッケージを追加。公開 API として data, research, ai, execution, strategy, monitoring 等のサブパッケージを想定。
  - バージョン情報を src/kabusys/__init__.py にて __version__ = "0.1.0" として管理。

- 設定管理
  - src/kabusys/config.py を追加。
    - .env ファイル（.env, .env.local）と OS 環境変数の自動読み込み機能を実装（プロジェクトルート自動検出: .git または pyproject.toml）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト向け）。
    - .env のパースは export KEY=...、クォート内エスケープ、行内コメント等に対応する堅牢な実装。
    - 必須環境変数を取得する _require 関数、Settings クラスを提供（J-Quants / kabu / Slack / DB パス / 環境モード / ログレベル等）。
    - 環境値のバリデーション（KABUSYS_ENV の許容値、LOG_LEVEL の検証など）。
    - Path を返す DB パス（duckdb/sqlite）の expanduser 対応。

- データプラットフォーム（DuckDB ベース）
  - src/kabusys/data/* を追加（Calendar 管理、ETL、Pipeline 等）。
  - calendar_management.py
    - market_calendar を用いた営業日判定 API を提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - カレンダーデータがない場合は曜日（週末）ベースのフォールバックロジックを実装。
    - calendar_update_job: J-Quants API から差分取得し冪等的に保存する夜間バッチ処理（バックフィル・健全性チェックあり）。
    - DB のデータ欠損（NULL）に対する警告ログ、最大探索日数による infinite loop 回避等の安全策を実装。
  - pipeline.py / etl.py
    - ETLResult データクラスを実装し、ETL の実行結果（取得数・保存数・品質問題・エラー等）を表現。
    - 差分更新、バックフィル、品質チェックの方針を実装に反映。DuckDB テーブルの最大日付取得ユーティリティ等を提供。
    - data.etl で ETLResult を再エクスポート。

- 研究（Research）モジュール
  - src/kabusys/research/* を追加。
  - factor_research.py
    - Momentum, Volatility, Value（PER/ROE）等のファクター計算関数を実装:
      - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）。
      - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率等。
      - calc_value: raw_financials を用いた PER / ROE の算出（最新の報告日を使用）。
    - DuckDB のウインドウ関数・LAG/LEAD を利用した効率的な処理。
    - データ不足時（必要行数未満）は None を返す設計。
  - feature_exploration.py
    - calc_forward_returns: 複数ホライズン（デフォルト: 1,5,21 営業日）で将来リターンを一括取得。
    - calc_ic: スピアマン（ランク）相関による IC 計算（3 銘柄未満は None）。
    - rank: 同値は平均ランクで扱うランク関数（float の丸めで ties 対応）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー関数。
  - research パッケージ __init__ で主要関数を再エクスポート。

- AI（OpenAI）連携
  - src/kabusys/ai/* を追加。
  - news_nlp.py
    - raw_news と news_symbols を集約し、銘柄ごとのニュースをまとめて OpenAI（gpt-4o-mini, JSON mode）に投げるバッチ型のセンチメント分析機能（score_news）。
    - JST→UTC の時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を実装（calc_news_window）。
    - バッチ化（デフォルト最大 20 銘柄 / リクエスト）、記事数・文字数のトリム、レスポンスバリデーション、スコアクリッピング（±1.0）を実装。
    - リトライ（429・ネットワーク・タイムアウト・5xx）に対して指数バックオフの再試行ロジックを実装。
    - API キー未設定時は ValueError を送出。テスト用に _call_openai_api を patch できるよう設計。
    - DB 書き込みは部分置換（対象コードのみ DELETE→INSERT）で部分失敗時のデータ保護を実施（DuckDB executemany の注意点考慮）。
  - regime_detector.py
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み70%）とニュース由来のマクロセンチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - マクロニュース抽出、OpenAI 呼び出し（JSON 出力期待）、堅牢なリトライ・フォールバック（失敗時 macro_sentiment=0.0）を実装。
    - DB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を行う。
    - ルックアヘッドバイアス防止のため内部で datetime.today()/date.today() を参照しない設計。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security / Notes
- OpenAI API キーは引数経由または環境変数 OPENAI_API_KEY で供給する必要がある。未設定時は ValueError を送出する箇所あり（news_nlp.score_news, regime_detector.score_regime）。
- .env 自動ロード時、既存の OS 環境変数は保護される（.env.local は override=True だが protected set により OS 環境変数は上書きされない）。
- DB 書き込みはトランザクションで囲み、失敗時に ROLLBACK を試行。ROLLBACK 自体が失敗した場合は警告ログを出力する。
- DuckDB 固有の注意:
  - executemany に空リストを渡せない古いバージョン（例: 0.10）への互換性を考慮して空チェックを行っている。
  - 日付値の取り扱いで isoformat を利用する等の互換性配慮あり。

### Known limitations / TODO
- 一部ファクター（PBR・配当利回り等）は未実装（calc_value の注記）。
- news_nlp と regime_detector はそれぞれ独立で OpenAI 呼び出しの内部実装を持つ（テスト容易性とモジュール結合低減のため）。将来的に共通化の検討余地あり。
- jquants_client 等外部クライアントの実装はこの差分から参照する想定だが、依存関係や API 仕様の変更に合わせて修正が必要。
- 実運用にあたってはログ出力・エラーハンドリングの詳細チューニング、スケーリング、コスト管理（API 呼び出し回数）等の追加検討が必要。

---

参考: 本 CHANGELOG はソースコードの内容・コメント・設計ノートから推測して作成しています。実際のリリースノートとして公開する前に、開発チームによる内容確認と日付の確定を行ってください。