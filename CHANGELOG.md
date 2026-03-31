CHANGELOG
=========
すべての変更は Keep a Changelog の形式に従って記載しています。  
慣例により重要な変更点はカテゴリ別（Added / Changed / Fixed / Deprecated / Removed / Security）でまとめています。

[Unreleased]
------------

- （今後の変更記録用）

[0.1.0] - 2026-03-31
-------------------

Added
- 初回リリース。KabuSys コードベースの基本機能を実装。
- パッケージ公開情報
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - __all__ による公開モジュール: data, strategy, execution, monitoring
- 環境設定管理
  - 環境変数・.env 読み込みユーティリティを実装（kabusys.config.Settings）。
  - プロジェクトルート自動検出: .git または pyproject.toml を基準に探索（ワーキングディレクトリに依存しない）。
  - .env パーサ: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
  - 自動ロード順序: OS 環境変数 > .env.local（上書き） > .env（未上書き）。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
  - 保護された既存 OS 環境変数を上書きしない仕組み（protected set）。
  - 設定項目（例）: JQUANTS_REFRESH_TOKEN, KABU_API_*, SLACK_BOT_TOKEN/SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL 等。バリデーション（許容値チェック）を実装。
- AI 関連
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を基に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメント（ai_scores）を生成・保存。
    - バッチサイズ、文字数・記事数上限、JSON mode 利用、レスポンス検証（results リスト・コード整合性・数値検証）を実装。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ。失敗時は部分スキップして他銘柄を保護する設計。
    - DuckDB の executemany 空リスト問題への対処（空時は実行しない）。
    - calc_news_window により JST ベースのニュース集計ウィンドウを明確に定義（ルックアヘッドを防止）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロセンチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書込み。
    - マクロセンチメントは raw_news からマクロキーワードで抽出した記事タイトルを LLM に評価させる方式。記事なしまたは API 失敗時はフォールバック macro_sentiment=0.0。
    - OpenAI 呼び出しは専用ラッパーを使用し、テスト時に差し替え可能な設計。
    - ルックアヘッドバイアス対策（target_date 未満のみ参照、datetime.today()/date.today() を直接参照しない）。
- データプラットフォーム（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - market_calendar テーブルを利用した営業日判定、前後営業日取得、期間内営業日列挙、SQ日判定などのユーティリティを提供。
    - DB 登録値を優先しつつ、データ未取得日は曜日ベースでフォールバックする一貫した挙動。
    - calendar_update_job による J-Quants からの差分取得と冪等保存、バックフィル・健全性チェックを実装。
  - ETL パイプライン（pipeline）
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - 差分取得・保存・品質チェック（quality）を組み合わせる設計。backfill による後出し修正吸収方針。
    - DuckDB テーブル存在チェックや最大日付取得ユーティリティを実装。
- 研究（kabusys.research）
  - factor_research
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR・相対 ATR）、Value（PER, ROE）等のファクター計算関数を実装。
    - DuckDB SQL を用いた高速集計、データ不足時の None 返却などの堅牢な実装。
  - feature_exploration
    - 将来リターン計算（任意ホライズン）、Spearman ベースの IC（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等の外部依存を使わずに標準ライブラリと DuckDB で完結する設計。
- テスト・運用性を考慮した設計
  - OpenAI 呼び出し関数はモジュール毎に差し替え可能（unittest.mock.patch でのモック化を想定）。
  - API 失敗時に例外を上げずフォールバックする箇所を多数実装（フェイルセーフ）、部分失敗時も DB の既存データを保護する方針。
  - DuckDB 互換性を考慮した実装（executemany の空リスト回避など）。

Changed
- （初回リリースにつき該当なし）

Fixed
- （初回リリースにつき該当なし）

Deprecated
- （初回リリースにつき該当なし）

Removed
- （初回リリースにつき該当なし）

Security
- （初回リリースにつき該当なし）

Notes（実装上の重要事項・既知の制約）
- LLM 関連は外部 API（OpenAI）に依存。API キーは api_key 引数または環境変数 OPENAI_API_KEY で指定。未設定時は ValueError を送出する箇所あり。
- ニュースウィンドウ・レジーム判定等はルックアヘッドバイアス防止のため target_date を明示的に渡す必要がある。内部で現在日時を参照しない設計。
- ai モジュールは JSON mode のレスポンスを期待しているが、受信データの前後に余計なテキストが混入するケースに対しては最外の {} を抽出して復元する処理を行う。
- DuckDB バージョン差異に対する互換措置を多数実装している（例: executemany の空リスト、リスト型バインド回避）。
- .env のパーシングロジックは柔軟だが、異常な書式の .env に対しては無視または警告を出す挙動となる。

開発者向け補足
- 各モジュールはテスト容易性を考慮して設計されています（API 呼び出しの差し替えポイント、明確な入出力、DuckDB 接続注入など）。
- 将来的な改善候補: エンドツーエンドの統合テスト・モックサーバを用いた OpenAI/ J-Quants の挙動検証、パフォーマンス測定（大規模データでのバッチ処理最適化）。

--- 
（本 CHANGELOG はコード内容から推測して作成しています。実際のリリースノート作成時はコミット履歴や PR 説明を参照のうえ調整してください。）