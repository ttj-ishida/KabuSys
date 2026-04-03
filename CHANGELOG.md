# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースから推測して作成したリリースノートです。

全般的な注意
- 本リリースでは DuckDB をデータレイヤとして想定した実装、OpenAI（gpt-4o-mini）を用いた NLP 評価、J-Quants など外部データソースとの連携用インターフェースが含まれます。
- 実装上の設計方針として「datetime.today()/date.today() に依存しない（ルックアヘッドバイアス防止）」「API 呼び出しはフェイルセーフで継続」「DB 書き込みは冪等性を重視」等が各モジュールに明記されています。

Unreleased
- （現在未リリースの変更はありません）

[0.1.0] - 2026-04-03
Added
- パッケージ初回リリース相当の実装を追加。
  - パッケージ名: kabusys、バージョン: 0.1.0
- 設定・環境変数管理（kabusys.config）
  - .env/.env.local をプロジェクトルートから自動読込（CWD に依存しない探索）。
  - export 構文、シングル/ダブルクォート・バックスラッシュエスケープ、インラインコメントの取り扱いに対応したパーサ実装。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を用意。
  - 必須環境変数チェック(_require) と Settings クラス（J-Quants / kabu API / LINE / DB /監視 /システム設定等のプロパティ）。
  - KABUSYS_ENV / LOG_LEVEL の値検証（許容値の制約）。
- AI モジュール（kabusys.ai）
  - news_nlp.score_news
    - raw_news / news_symbols を集約し、銘柄単位に記事をまとめて OpenAI へバッチ送信。
    - バッチサイズ、最大記事数/文字数制限、JSON Mode のレスポンス検証、スコアのクリップ（±1.0）を実装。
    - リトライ（429・ネットワーク断・タイムアウト・5xx）に対する指数バックオフを実装。
    - レスポンスの堅牢なパース（前後余分テキストから {} を抽出する復元処理含む）。
    - ai_scores テーブルへ（部分失敗を避けるため）取得成功分のみ DELETE→INSERT による置換。
    - テスト容易性のため _call_openai_api をモック差替え可能に設計。
  - regime_detector.score_regime
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定・保存。
    - prices_daily と raw_news を参照、calc_news_window を用いたウィンドウ計算、OpenAI 呼び出しは独立実装。
    - API 失敗時は macro_sentiment=0.0 にフォールバックし継続。
    - market_regime への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）と ROLLBACK の扱い。
- データ・ETL（kabusys.data）
  - calendar_management
    - market_calendar を基にした営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB にデータがない場合は曜日ベースのフォールバック（週末を非営業日とする）。
    - calendar_update_job：J-Quants からの差分取得 → market_calendar へ冪等保存（バックフィル・健全性チェック含む）。
  - pipeline / etl
    - ETLResult データクラスを公開（ETL 実行結果の構造化、品質問題やエラーの記録、to_dict 変換を提供）。
    - ETL の設計方針（差分更新、backfill、品質チェックの収集継続方針、id_token 注入可能）を反映したコード骨格。
  - etl モジュールは pipeline.ETLResult を再エクスポート。
- リサーチ（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離（データ不足時は None を返す）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務を参照して PER / ROE を計算（EPS が無効な場合は None）。
    - 実装は DuckDB 上の SQL と Python を組み合わせて実行し、(date, code) をキーとする辞書リストを返す。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン先の将来リターンをまとめて取得する SQL 実装（ホライズンのバリデーションあり）。
    - calc_ic: スピアマン（ランク）による Information Coefficient 計算（結合・None 除外・最小レコード数制約）。
    - rank: 同順位を平均ランクとするランク付け。
    - factor_summary: 基本統計量（count / mean / std / min / max / median）を算出。
- 依存・統合
  - DuckDB を想定した SQL 実行（duckdb.DuckDBPyConnection を引数に取る）。
  - OpenAI SDK（openai.OpenAI）を利用する設計（API キーは引数 or OPENAI_API_KEY 環境変数）。
  - J-Quants クライアント用のインターフェース（kabusys.data.jquants_client を参照）を利用する想定。
- ログ・例外処理
  - 各処理での詳細な logger 呼び出しと、失敗時のフォールバック（警告ログを出して中断せず継続）を多用。
  - DB 書き込み時のトランザクション（BEGIN/COMMIT/ROLLBACK）や ROLLBACK 失敗の警告ログを実装。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 環境変数に機密情報（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を要求。自動 .env 読込の挙動に注意（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。

Notes / 実装上の制約と設計意図（重要）
- ルックアヘッドバイアス対策として datetime.today()/date.today() をモジュール内部で直接参照しない実装方針（すべて target_date を明示的に受け取る）。
- API 呼び出しは冪等性・フォールバックを優先。OpenAI の失敗は基本的に局所的フォールバック（0.0 等）で処理を継続する設計。
- ai/news モジュールは厳密な JSON 出力を期待するが、LLM の出力が前後に余計な文字列を含む場合に備えた復元ロジックを持つ。
- DuckDB の executemany の挙動（空リスト不可など）を考慮した実装（空チェックを入れてから executemany を呼ぶ）。
- OpenAI クライアント呼び出し用の内部関数はテストで差し替え可能（mock で置換可能）にしてある。
- calendar_update_job や ETL 実行は外部 API（J-Quants）依存 → 実行環境での API キー・ネットワークの準備が必要。

今後の検討事項（推奨）
- 単体テスト・統合テストの整備（特に OpenAI / J-Quants 呼び出しをモックするテストスイート）。
- パフォーマンス改善（大規模データ時の SQL チューニング、並列処理の導入など）。
- エラー / 障害時のアラート機構（LINE 通知等）やモニタリング統合。
- ai スコアリングのモデル選択・プロンプト最適化とモデルコスト管理。

---
この CHANGELOG はコードから推測して作成しています。実際のリリースノートや運用上の注意は、プロジェクト責任者の情報に基づき適宜調整してください。