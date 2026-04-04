# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

※初期リリース (0.1.0) の内容は、リポジトリ内ソースコードから推測して記載しています。

## [Unreleased]

## [0.1.0] - 2026-04-04
初回公開リリース。

### Added
- パッケージ基盤
  - パッケージ名: `kabusys`。バージョン `0.1.0` を定義（src/kabusys/__init__.py）。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ で指定。

- 環境設定 / ロード
  - 環境変数管理モジュールを追加（src/kabusys/config.py）。
    - プロジェクトルート検出: `.git` または `pyproject.toml` を基準として自動検出し、そこから `.env` / `.env.local` を相対パスで読み込む実装を提供（CWD に依存しない）。
    - .env パーサーの実装: コメント、`export KEY=val` 形式、クォート（シングル/ダブル）とバックスラッシュエスケープの処理、行内コメントの扱い等に対応。
    - 自動読み込みの無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - 環境変数保護: OS 環境変数は保護（`.env.local` の override は OS 環境変数を上書きしない）。
    - Settings クラスを公開 (`settings`): J-Quants、kabu API、LINE、DB パス、監視閾値、環境種別（development / paper_trading / live）・ログレベル等のプロパティを提供。入力バリデーション（許容値チェック）を備える。

- AI（OpenAI）連携
  - ニュース NLP スコアリング (`kabusys.ai.news_nlp`) を追加。
    - raw_news / news_symbols から記事を銘柄毎に集約し、OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信して銘柄ごとのセンチメント（-1.0〜1.0）を算出。
    - チャンク単位処理（デフォルト _BATCH_SIZE=20）、1 銘柄あたり記事数・文字数上限（トリム）を実装。
    - API エラー（429、ネットワーク、タイムアウト、5xx）に対する指数バックオフリトライを実装。再試行上限超過やパース失敗時はフェイルセーフで該当チャンクをスキップ。
    - レスポンス検証ルールを厳格化（JSON 抽出、results リストの検証、code の整合性、数値検査、スコアの ±1.0 クリップ）。
    - idempotent な DB 書き込み（対象コードのみ DELETE → INSERT）を行い、部分失敗時でも他コードの既存スコアを保護。
    - 公開関数: score_news(conn, target_date, api_key=None) を提供。

  - 市場レジーム判定モジュール (`kabusys.ai.regime_detector`) を追加。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - マクロキーワードで raw_news のタイトルをフィルタし、OpenAI（gpt-4o-mini）でマクロセンチメントを算出。API 失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。
    - レジームスコア合成と market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - 公開関数: score_regime(conn, target_date, api_key=None)。

  - 両モジュールとも OpenAI クライアント呼び出し部はテスト用に差し替え可能（内部 _call_openai_api を patch 可能に設計）。

- データプラットフォーム（DuckDB ベース）
  - ETL パイプラインの結果表現を追加（src/kabusys/data/pipeline.py）。
    - ETLResult dataclass を定義（取得数・保存数・品質問題・エラー等を格納）。to_dict() により品質問題を辞書化。
  - ETL ユーティリティの公開インターフェースを追加（src/kabusys/data/etl.py が ETLResult を再エクスポート）。
  - カレンダー管理モジュールを追加（src/kabusys/data/calendar_management.py）。
    - JPX カレンダー（market_calendar テーブル）を使った営業日判定・前後営業日の探索・営業日リスト取得（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にカレンダーがない場合は曜日（平日）ベースでフォールバックする堅牢な設計。
    - 夜間バッチ更新ジョブ calendar_update_job(conn, lookahead_days=...) を実装。J-Quants クライアント経由で差分取得 → 保存（バックフィル、健全性チェックを含む）。
    - 最大探索範囲やバックフィル、健全性チェック等の保護機構を実装。

- リサーチ / ファクター解析
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum（1m/3m/6m リターン、200日 MA 乖離）、Volatility（20日 ATR）、Value（PER、ROE）等の計算関数を実装。
    - DuckDB のウィンドウ関数を活用して効率的に計算。データ不足時は None を返す設計。
    - 公開関数: calc_momentum, calc_volatility, calc_value。
  - 特徴量探索モジュールを追加（src/kabusys/research/feature_exploration.py）。
    - 将来リターン計算（calc_forward_returns）、IC（Spearman ρ）計算（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB で実装。
  - research パッケージの __all__ に主要関数をまとめてエクスポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数の自動ロードはオプション化（KABUSYS_DISABLE_AUTO_ENV_LOAD）されており、テストや CI 環境での秘密漏洩リスクを低減。

### Notes / 設計方針（重要）
- ルックアヘッドバイアス対策: AI モジュール・リサーチ関数ともに内部で datetime.today() / date.today() を参照せず、必ず呼び出し側から target_date を与える方式で設計。
- フェイルセーフ: OpenAI API の障害やパースエラーは基本的に例外を上位へ投げずデフォルト値（0.0 等）で処理を継続する実装。DB 書き込み失敗時はトランザクションをロールバックして例外伝播。
- DuckDB 互換性配慮: executemany に対する空リスト禁止等のバージョン差異を回避する実装（書き込み前の空チェック、個別 DELETE 実行等）。
- OpenAI 呼び出しは JSON Mode を利用し厳格なレスポンス形式を期待するが、実運用上の雑多な出力に対しても復元ロジック（最外側の {} 抽出）を入れている。
- idempotency: カレンダー・AI スコア・レジーム等の DB 書き込みは冪等（上書き/DELETE→INSERT）で実装。

### Known limitations / TODO（ソースから推測）
- strategy / execution / monitoring の実体がこの差分では未提示（__all__ に名前はあるがコードは未表示）。実行・発注周りの実装は別所にあるか今後追加予定。
- J-Quants クライアント（jquants_client）や一部 data モジュールの実装は別ファイルに依存している（リポジトリ内で別途提供されていることを想定）。

---

今後のリリースでは、実取引連携（kabu 発注実装）、モニタリングエージェント、追加の品質チェックルール・テストカバレッジ拡充、ドキュメント（使用例・運用手順）を追記することが想定されます。