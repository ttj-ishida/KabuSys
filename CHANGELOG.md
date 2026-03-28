CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用しています。

[Unreleased]
------------

- （現在のコードベースは初期リリース相当の状態が含まれているため未リリースの変更はありません）

[0.1.0] - 2026-03-28
-------------------

Added
- パッケージ初期リリース。
  - バージョン: 0.1.0（src/kabusys/__init__.py に __version__ を定義）

- コア / 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数の自動読み込み機能を実装
    - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索（CWD に依存しない）
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能（テスト用）
    - OS 環境変数を保護するための protected キーセットを導入（.env の上書きを制御）
  - .env パーサを実装（kabusys.config._parse_env_line）
    - export 前置、単/二重クォート、バックスラッシュエスケープ、行内コメントの取り扱いに対応
    - 無効行（空行、コメント、不正フォーマット）は無視
  - Settings クラスを提供（settings インスタンスをエクスポート）
    - J-Quants、kabuステーション、Slack、DBパス（DuckDB/SQLite）、環境種別（development/paper_trading/live）、ログレベルの取得とバリデーション
    - env/log_level の許容値チェック、is_live / is_paper / is_dev の便宜プロパティ
    - 必須環境変数未設定時は説明付きの ValueError を送出

- データ取得／カレンダー管理 (kabusys.data.calendar_management)
  - JPX カレンダーの夜間バッチ更新ロジックを実装（calendar_update_job）
    - J-Quants API からの差分取得、バックフィル（直近 N 日）、健全性チェック（極端な future 日付はスキップ）を実装
    - 保存は冪等に（ON CONFLICT DO UPDATE 相当を想定）
  - 営業日判定ユーティリティを提供
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - DB 登録値優先、未登録日は曜日ベースでフォールバック
    - 最大探索日数の上限設定で無限ループを防止
  - market_calendar テーブル未取得時のフォールバック挙動を明確化（曜日ベース）

- ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
  - ETLResult データクラスを定義し公開（kabusys.data.etl で再エクスポート）
    - ETL の取得数／保存数、品質問題、エラー概要を保持
    - has_errors / has_quality_errors 等の便宜プロパティ、監査用の to_dict を実装
  - 差分更新・バックフィル・品質チェックを想定した設計（DataPlatform.md に準拠）
    - 最小取得開始日、カレンダー先読み、デフォルトバックフィル日数などの定数定義
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティを実装

- ニュース NLP / AI (kabusys.ai.news_nlp, kabusys.ai.regime_detector)
  - ニュースセンチメントスコアリング機能（news_nlp.score_news）
    - タイムウィンドウ（JST 前日15:00〜当日08:30）に基づく記事集約ロジックを実装（calc_news_window）
    - raw_news と news_symbols から銘柄ごとに記事を集約、記事数/文字数でトリム
    - OpenAI（gpt-4o-mini）へバッチ送信（1回に最大 _BATCH_SIZE=20 銘柄）
    - JSON mode を使った応答バリデーション（厳密な {"results": [...] } 形式を期待）
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ
    - レスポンスの検証とスコアの ±1.0 クリップ、部分成功時でも既存スコアを保護する安全な DB 書き込み（DELETE→INSERT）
    - DuckDB の executemany の制約に合わせた空パラメータ回避処理
    - テスト容易性のため _call_openai_api の差し替え（patch）を想定
  - 市場レジーム判定モジュール（regime_detector.score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次レジーム判定（bull/neutral/bear）
    - news_nlp の calc_news_window を再利用してウィンドウを決定
    - OpenAI 呼び出しは専用の内部実装を持ち、retry/バックオフ、API エラーのフォールバック（macro_sentiment=0.0）を備える
    - DB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）と ROLLBACK 保護
    - API キー注入（引数 or OPENAI_API_KEY 環境変数）に対応し、未設定時は ValueError を投げる

- リサーチ／因子計算 (kabusys.research)
  - factor_research モジュール
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR 等）、Value（PER/ROE）を DuckDB + SQL で実装
    - データ不足時の安全な None 戻り、ターゲット日を基準としたクエリ実行でルックアヘッドを回避
    - 全関数は prices_daily / raw_financials のみ参照（外部 API に非依存）
  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns）: LEAD を使い複数ホライズンを1クエリで取得
    - IC（Information Coefficient; Spearman の ρ）計算（calc_ic）
    - ランク変換ユーティリティ（rank）とファクター統計サマリー（factor_summary）
    - pandas 等に依存せず標準ライブラリで実装
  - kabusys.research.__init__ で必要関数を再エクスポート

- パッケージ公開インターフェース
  - 主要モジュール（data, strategy, execution, monitoring）を __all__ に設定（将来の拡張を想定）

Changed
- （初期リリースのため変更履歴なし）

Fixed
- （初期リリースのため修正履歴なし）
  - ただし設計上、API 呼び出し失敗時に例外を投げずフォールバックするなど堅牢性向上策を実装済み

Security
- （該当なし）

Notes / 備考
- OpenAI 関連の呼び出しは gpt-4o-mini を前提とした実装（JSON mode）であり、API SDK の将来の変更（例: APIError の属性）にも耐性を持つように防御的に実装されています。
- DuckDB 固有の振る舞い（executemany の空リスト不可等）に合わせた実装・ワークアラウンドを含みます。
- 日付/時刻の扱いはルックアヘッドバイアスを避けるため、target_date を明示的に渡す設計です（内部で datetime.today()/date.today() を参照しない）。

今後
- strategy / execution / monitoring の具体実装、テストカバレッジ・ドキュメントの拡充、運用向けの監視/通知機能（Slack 連携など）の追加を予定しています。