# CHANGELOG

すべての注目すべき変更はここに記載します。本ファイルは Keep a Changelog の様式に準拠します。

最新の変更は上に配置しています。

## Unreleased

（なし）

## [0.1.0] - 2026-04-03

初回公開リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。主な追加点・設計方針・注意点は以下の通りです。

### Added（追加）
- パッケージ基盤
  - パッケージメタ情報: kabusys v0.1.0。公開モジュールは data, research, ai, execution, monitoring 等を想定（__all__ に data, strategy, execution, monitoring を設定）。
- 環境設定管理（kabusys.config）
  - .env 自動読込機能（プロジェクトルートを .git / pyproject.toml から探索）。
  - .env / .env.local の読み込み順と上書きルール（OS 環境変数保護）。
  - .env パースの強化（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント扱いの仕様）。
  - 自動読み込みを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスによる環境変数ラッピング（必須チェック、デフォルト値、パスの Path 化、数値変換、列挙検証）。
  - 既定の環境変数名・既定値を提供（例: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, CPU/MEMORY/DISK の閾値 等）。
- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news + news_symbols から銘柄毎に記事を集約し、OpenAI（gpt-4o-mini）で銘柄別センチメント（-1.0〜1.0）を評価して ai_scores テーブルへ書き込む機能。
    - 時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して扱う calc_news_window）。
    - バッチ処理（最大 20 銘柄 / API コール）、1 銘柄あたり最大記事数・文字数でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - JSON Mode を用いた厳密 JSON 応答想定と、レスポンス復元処理（前後テキストが混在する場合は最外の {} を抽出して再パース）。
    - リトライ/バックオフ戦略（429/ネットワーク断/タイムアウト/5xx を対象、指数バックオフ、上限回数）。
    - レスポンスバリデーション（results 配列、各要素の code/score チェック、未知コードは無視、スコアは ±1.0 にクリップ）。
    - 部分失敗時に既存データを守るため、書き込みは「対象コードを限定して DELETE → INSERT」を実施。
    - テスト容易性のため _call_openai_api の差し替え（patch）を想定。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出用キーワードリスト、OpenAI 呼び出しは JSON Mode、リトライ/バックオフ、API 失敗時は macro_sentiment=0 をフェイルセーフとして採用。
    - ルックアヘッドバイアス対策: target_date 未満のみ参照、datetime.today() を参照しない設計。
- リサーチ機能（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER, ROE）を DuckDB 上の prices_daily / raw_financials から計算する関数を実装。
    - データ不足時の None 扱い、結果は (date, code) をキーとする dict のリストで返却。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（スピアマンρ）計算、ファクター統計サマリー、ランク化ユーティリティを提供。
    - 外部依存なし（pandas 等不使用）、欠損／非有限数値処理の明確化。
- データ基盤（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録がない場合は曜日（平日）ベースでフォールバック。
    - 夜間バッチ更新 job（calendar_update_job）: J-Quants から差分取得 → 保存（jq.save_market_calendar）・バックフィル・健全性チェックを実装。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを公開（取得件数、保存件数、品質チェック問題、エラー等を保持）。
    - 差分取得・バックフィル・品質チェックの設計（quality モジュールと連携する想定）。
    - jquants_client を通じた取得/保存呼び出しを想定（差分取得、idempotent 保存）。
  - パイプラインの再エクスポート（kabusys.data.etl で ETLResult を再エクスポート）。

### Changed（設計上の注意 / 仕様）
- OpenAI 統合
  - デフォルトモデルは gpt-4o-mini を使用する設計に統一。
  - API キーは関数引数で注入可能（api_key）かつ環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を発生させ明示的に通知。
  - テスト容易性のため、内部の API 呼び出し関数はモジュール毎に分離（news_nlp と regime_detector で別実装）してモック可能にしている。
- DB 書き込み
  - ai_scores / market_regime などの書き込みは冪等性を意識（BEGIN/DELETE/INSERT/COMMIT または executemany を利用）。
  - DuckDB のバージョン差異（executemany に空リストを渡せない点）を考慮した条件分岐を実装。
- 時刻・タイムゾーン
  - ニュース窓は JST ベースで定義し、DB 比較は UTC naive datetime を用いる（明確な window_start/window_end を返す）。
  - ルックアヘッドバイアスを防ぐため、各処理は内部で datetime.today()/date.today() に依存しない設計（target_date を明示的に受け取る）。
- ロギング/障害耐性
  - 外部 API エラーは原則例外で打ち切らずログ出力してフェイルセーフ（スコア 0.0 やスキップ）で継続する箇所が多い（運用上の可用性重視）。
  - 重要な DB 操作失敗時はロールバックを試行し、発生した例外は上位に伝播することで明示的に対処可能。

### Fixed（実装時に考慮したエッジケース／安定性向上）
- .env パースの不備対策
  - export キーワード、クォート内のバックスラッシュエスケープ、インラインコメントの判定等に対応して読み込み精度を向上。
- OpenAI レスポンスの堅牢化
  - JSON パース失敗時に応答文字列から最外の JSON オブジェクトを抽出して再パースを試みる処理を追加（ノイズ混入への耐性）。
  - レスポンス内の code が整数で返るケースを考慮して文字列化して照合する等の互換性担保。
- DuckDB の取り扱い
  - 日付変換ユーティリティ（_to_date）やテーブル存在確認ユーティリティを追加して DuckDB の戻り値差異に対応。
  - executemany の空リスト禁止の回避ロジックを追加。

### Notes（注意事項 / 既知の制約）
- OpenAI API 呼び出しは通信コストとレート制限の影響を受けます。運用時は API キー管理・呼び出し頻度に注意してください。
- news_nlp のバッチサイズ・文字数上限は現時点のトークン/レスポンス制約に合わせた保守的な設定です。将来のモデルやトークン計算に応じて調整が必要になります。
- DuckDB バージョンの違い（特に executemany の挙動）に依存する箇所があります。運用環境での DuckDB バージョン確認を推奨します。
- calendar_update_job は J-Quants クライアント（jquants_client）の実装に依存します（fetch/save 関数のエラーはゼロ件扱いで安全に無視）。
- Settings が必須とする環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は未設定時に ValueError を投げます。初期セットアップ時は .env.example をもとに .env を作成してください。

---

今後の予定（候補）
- strategy / execution / monitoring モジュールの具体的な注文ロジック・監視エージェントの実装
- ロギング設定の統合（構成ファイル・外部ロギングサービス連携）
- 単体テスト・統合テストの追加（OpenAI 呼び出しのモック、DuckDB のテスト DB）
- ドキュメント（使用例、運用手順、環境変数一覧、テーブルスキーマ）を拡充

（以上）