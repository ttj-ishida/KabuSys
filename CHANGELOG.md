CHANGELOG
=========

すべての重要な変更は "Keep a Changelog" の形式で記載します。
このファイルはコードベースの現在の状態（推測に基づく）を反映した初回リリース向けの変更履歴です。

フォーマット:
- 変更はカテゴリ別（Added / Changed / Fixed / Security / Deprecated / Removed）に整理しています。
- 日付は本ドキュメント作成日（2026-03-29）を使用しています。

Unreleased
----------
（未リリースの変更はここに記載）

0.1.0 - 2026-03-29
------------------

Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys、__version__ = "0.1.0"
  - パブリックサブパッケージ: data, strategy, execution, monitoring を __all__ で公開

- 環境設定 / ロード機能（kabusys.config）
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動ロードする仕組みを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用）。
  - .env パーサーは以下に対応：
    - export KEY=val 形式
    - シングル/ダブルクォート値（バックスラッシュエスケープ対応）
    - コメントの扱い（クォート外の # をインラインコメントとして扱う際の細かなルール）
  - Settings クラスを提供（環境変数の取得ラッパー）
    - 必須キー取得時に未設定なら ValueError を送出（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）
    - デフォルト値を持つ設定（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABUSYS_ENV）
    - KABUSYS_ENV / LOG_LEVEL の値バリデーション（許容値チェック）
    - is_live / is_paper / is_dev ヘルパーを提供

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON モードでバッチ問い合わせして銘柄別センチメント（ai_scores）を作成
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST 相当）を calc_news_window で提供
    - バッチ処理（_BATCH_SIZE=20）、記事数 / 文字数上限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）によるトリム
    - JSON 応答の堅牢なバリデーション (_validate_and_extract)
    - リトライ戦略（RateLimit / ネットワーク / タイムアウト / 5xx に対する指数バックオフ、上限設定）
    - DuckDB への安全な置換保存（DELETE → INSERT、部分失敗時に既存データを保護）
    - テスト容易性のため _call_openai_api のモック差し替えを想定
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）200日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して market_regime を日次判定
    - レジーム判定フロー実装（MA計算、マクロニュース抽出、OpenAI 呼び出し、スコア合成、冪等な DB 書き込み）
    - LLM 呼び出し失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）
    - OpenAI 呼び出しは専用関数で分離（モジュール間の結合低減）
    - 冪等性を担保した DB トランザクション処理（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）

- データプラットフォーム（kabusys.data）
  - カレンダー管理（calendar_management）
    - market_calendar を基に営業日判定 / next / prev / 範囲取得 / SQ判定ロジックを実装
    - market_calendar が未取得の際は曜日ベース（土日休場）でフォールバック
    - calendar_update_job: J-Quants API から差分取得、バックフィル（直近 _BACKFILL_DAYS 日）と健全性チェックを備えた夜間バッチ
    - DB 登録値優先、未登録日は曜日フォールバックで一貫した結果を返す設計
  - ETL パイプライン（pipeline）
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）
    - 差分取得、保存（jquants_client 経由の idempotent 保存）、品質チェック（quality モジュールの問題収集）を行う設計方針を実装
    - DuckDB の互換性を考慮したユーティリティ（テーブル存在チェック、最大日付取得など）
    - backfill_days といった再取得パラメータのサポート

- 研究/リサーチ機能（kabusys.research）
  - ファクター計算（factor_research）
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性指標（20日平均売買代金、出来高比率）、バリュー（PER/ROE）を DuckDB の prices_daily / raw_financials から計算
    - データ不足時は None を返す設計
  - 特徴量解析ユーティリティ（feature_exploration）
    - 将来リターン計算（calc_forward_returns、可変ホライズン対応）
    - IC（Information Coefficient）計算（スピアマンのランク相関）
    - ランク付けユーティリティ（rank、同順位は平均ランク）
    - ファクター統計サマリ（factor_summary）
  - zscore_normalize をデータモジュール側から再利用可能に統合（kabusys.data.stats 経由）

- 品質・堅牢性に関する共通設計
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照するコードを極力避け、target_date を引数で与える設計
  - OpenAI / 外部 API 呼び出しは明示的にリトライ・フォールバックを実装（失敗時にも例外ではなく安全に継続する箇所が多い）
  - DuckDB 固有の互換性回避（executemany に空リストを渡さないチェック、日付型変換ユーティリティ等）
  - ロギングを多用し、警告・情報ログで異常時の挙動を記録

Changed
- （初回リリースのため該当なし）

Fixed
- DuckDB の executemany に対する空パラメータ問題に対応（空リストを渡さないガードを追加）
- API 応答パースの堅牢化（JSON 前後の余分なテキストが混ざるケースから復元してパースを試みる）

Security
- OpenAI API キーは環境変数（OPENAI_API_KEY）または明示的引数で注入する方式を採用し、直接コードに埋め込まない運用を想定

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Notes / 実装上の重要な設計判断（要点）
- idempotent な DB 操作を重視：既存レコードの上書きや部分失敗時の保護を行う実装（DELETE → INSERT のパターン等）
- フォールバック戦略：外部 API（OpenAI / J-Quants）失敗時はサービス全体を停止させず、可能な範囲で継続（例：macro_sentiment=0.0）
- テスト容易性：OpenAI 呼び出し点を差し替えられるように分離（unittest.mock.patch で差し替え可能）
- ルックアヘッドバイアス回避：全ての時間依存処理は target_date に基づく計算で実装
- DuckDB の挙動差異（バージョン互換性）を考慮した実装やエラー回避ロジックを多数導入

今後の改善の余地（推測）
- strategy / execution / monitoring サブパッケージの具体実装（現行コードベースでは公開インターフェースのみ確認）
- テストカバレッジ強化（特に OpenAI のエラー挙動や J-Quants クライアント周り）
- スケーリングや並列実行時のレート制御/コネクション管理の追加

--- 
（以上）