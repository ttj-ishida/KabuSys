CHANGELOG
=========
すべての重要な変更を記録します。本ファイルは「Keep a Changelog」の様式に準拠します。

フォーマット:
- 変更はセマンティックバージョニングに従います。
- 各リリースは Added / Changed / Fixed / Removed / Security のカテゴリで整理します。

Unreleased
----------
（現在の開発中の変更をここに記載してください）

0.1.0 - 2026-03-31
-----------------
初期リリース。日本株の自動売買／リサーチ／データ基盤向けのライブラリ群を提供します。
主な追加点・特徴は以下の通りです。

Added
- パッケージ基盤
  - kabusys パッケージの初期モジュールを追加。
  - パッケージバージョンは __version__ = "0.1.0"。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - 自動読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - 高度な .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープに対応）。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得（必須設定は例外を投げる）。
  - 設定項目例: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、DUCKDB_PATH、PID_FILE_PATH、KABUSYS_ENV、LOG_LEVEL など。
  - KABUSYS_ENV / LOG_LEVEL 値検証（許容値チェック）を実装。

- AI 関連モジュール (kabusys.ai)
  - ニュースセンチメント解析（score_news）
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し銘柄ごとの ai_score を ai_scores テーブルへ書き込み。
    - JSON Mode を使った厳密なレスポンス想定と、前後の余計なテキストが混ざる場合の復元ロジックを含む堅牢なパースとバリデーション。
    - バッチサイズ、記事文字制限、チャンクごとのリトライ（429/ネットワーク/タイムアウト/5xx）・指数バックオフを実装。
    - API キーは引数注入可能（テスト容易化）。失敗時は例外を出すかスキップ（フェイルセーフ）する挙動を明記。
    - DuckDB executemany に関する互換性考慮（空リスト渡し回避）。
  - 市場レジーム判定（score_regime）
    - ETF (code=1321) の 200 日移動平均乖離とマクロニュースの LLM センチメントを重み合成して market_regime テーブルへ書き込み。
    - LLM 呼び出しは独立実装。最大リトライや 5xx の扱い、フェイルセーフで macro_sentiment=0.0 を採用。
    - レジーム出力ラベル: "bull" / "neutral" / "bear"、スコアは -1.0〜1.0 にクリップ。
  - テスト容易性を考慮し、_call_openai_api をパッチ差替え可能に設計。

- データ基盤 (kabusys.data)
  - カレンダー管理（calendar_management）
    - market_calendar を元に営業日判定と翌営業日／前営業日・期間取得ユーティリティを提供。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - calendar_update_job により J-Quants からの差分取得 → 冪等保存（ON CONFLICT）を想定。バックフィル・健全性チェックを実装。
  - ETL パイプライン（pipeline）
    - ETLResult データクラスを提供し、ETL の取得件数・保存件数・品質問題・エラーを整理可能に。
    - 差分更新、バックフィル、品質チェック、id_token 注入などの設計方針を実装方針として含む。
  - etl モジュールから ETLResult を再エクスポート。

- リサーチ（kabusys.research）
  - factor_research
    - Momentum（1M/3M/6M、ma200乖離）、Volatility（20日ATR、相対ATR）、Value（PER、ROE）などのファクター計算関数を追加。
    - DuckDB を使った SQL ベース実装で、prices_daily / raw_financials 参照のみ。結果は (date, code) をキーとする辞書リストで返す。
    - データ不足時の None 戻しやログ出力など堅牢性を考慮。
  - feature_exploration
    - 将来リターン calc_forward_returns（複数ホライズン対応）、IC（calc_ic：スピアマンランク相関）、rank、factor_summary（count/mean/std/min/max/median）を実装。
    - pandas など外部依存を使わず標準ライブラリ + DuckDB で実装。
  - 研究向けユーティリティ（zscore_normalize は kabusys.data.stats から利用可能として再エクスポート）。

Changed
- （初期リリースのため履歴はなし。ただし各モジュールにおいて「ルックアヘッドバイアス防止」「テスト容易性」「フェイルセーフ」等の設計選択を明記。）

Fixed
- （初期リリースのため履歴はなし。ただし実装上、以下の安定化措置を実施）
  - .env パーサでのクォート・エスケープ処理、コメント判定の精緻化。
  - OpenAI API レスポンスのパース失敗・API エラー時に例外を投げずフォールバックする処理を整備。
  - DuckDB の executemany に対する空リスト渡し回避ロジックを導入。

Notes / Implementation details
- すべての日付処理は date / datetime (naive UTC 想定) で統一し、datetime.today() / date.today() の乱用によるルックアヘッドバイアスを防止する設計を採用。
- OpenAI モデルは gpt-4o-mini を想定し、JSON モード（response_format={"type":"json_object"}）での利用を前提にしている。
- AI スコアは -1.0〜1.0 にクリップすることで過度な外れ値を抑制。
- DB 書き込みは可能な限り冪等（DELETE→INSERT や ON CONFLICT）で実装し、失敗時はロールバックを試みる。ロールバック失敗時はログに警告を出力。
- ネットワーク/API エラーに対しては再試行(指数バックオフ)を行い、再試行失敗時は安全なデフォルト（例: macro_sentiment=0.0）で続行するフェイルセーフ設計。
- テスト容易性のため多くの内部外部接続ポイント（OpenAI クライアント生成や _call_openai_api、api_key の引数注入など）を差し替え可能にしている。

Acknowledgements / External APIs
- J-Quants / J-Quants API をデータ取得先として想定（jquants_client 経由）。
- OpenAI API を NLP / センチメント評価に利用（API キーは環境変数 OPENAI_API_KEY または関数引数で提供）。

今後の予定（提案）
- strategy / execution / monitoring の具体的な注文ロジック・監視機能の実装とテスト。
- ai モジュールのエンドツーエンドテスト（モック化）と API コールコスト最適化。
- DuckDB スキーマ定義・初期化ユーティリティの追加。
- .env.example やドキュメント整備、CI ワークフロー追加。

-- END --