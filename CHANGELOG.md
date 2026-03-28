# Changelog

すべての注目すべき変更をここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  
リリースはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-28 (初版)
初回リリース。日本株自動売買・データ基盤のコアライブラリを実装しました。主な追加項目は以下のとおりです。

### Added
- パッケージの基礎
  - パッケージ名: `kabusys`、バージョン `0.1.0`。
  - 公開モジュール: data, strategy, execution, monitoring（__init__ でのエクスポート）。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD 非依存）。
    - 自動ロードを無効にするためのフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env パーサーは下記の振る舞いをサポート:
    - `export KEY=val` 形式対応、シングル／ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い（クォート有無による判定）。
  - 必須環境変数の取得ラッパー `_require()` を提供。
  - アプリ設定クラス `Settings` を実装（J-Quants トークン、kabu API 設定、Slack トークン・チャネル、DB パス、環境種別・ログレベル判定など）。
    - デフォルト値（例: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH）を用意。
    - `KABUSYS_ENV` / `LOG_LEVEL` の検証（許容値チェック）。
    - `is_live` / `is_paper` / `is_dev` の補助プロパティ。

- AI モジュール（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとのテキストを作成。
    - OpenAI（gpt-4o-mini, JSON mode）へバッチ送信（最大 20 銘柄／チャンク）してセンチメントを取得。
    - エラー耐性: 429/ネットワーク/タイムアウト/5xx に対する指数バックオフ・リトライ。その他エラーはスキップして継続（フェイルセーフ）。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code/score の検証、スコアの ±1.0 クリップ）。
    - DuckDB への書き込みは冪等化（DELETE → INSERT）し、部分失敗時に既存スコアを保護。
    - テスト容易性のため OpenAI 呼び出し関数を差し替え可能（patch 可能）。
    - 時間ウィンドウ計算ロジック（JST 基準の前日 15:00 ～ 当日 08:30 を UTC に変換）を提供（calc_news_window）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースフィルタリング用キーワード集合と最大記事数を実装。
    - OpenAI 呼び出しは専用の実装で、API エラー時は macro_sentiment=0.0 にフォールバック。
    - レジームは score を閾値でラベル化し、結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。失敗時は ROLLBACK を試行して例外を透過。

- データ基盤ユーティリティ（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分取得・保存・品質チェックのワークフロー設計を実装。
    - ETL 実行結果を表す dataclass `ETLResult` を公開（to_dict メソッドで品質問題のシリアライズ対応）。
    - DuckDB を想定したテーブル存在チェック、最大日付取得ユーティリティ等を実装。
  - ETL の再エクスポート（kabusys.data.etl は ETLResult を再エクスポート）。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）を実装。J-Quants クライアント経由で差分取得し保存。
    - 営業日判定ロジック: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - DB にカレンダーがない場合は曜日ベース（平日）でフォールバック。DB 登録値を優先し未登録日は一貫したフォールバックを行う設計。
    - 最大探索日数やバックフィル、健全性チェック（将来日が過度に進んでいる場合のスキップ）を実装。

- リサーチ・分析ユーティリティ（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR / ATR 比率）、バリュー（PER / ROE）などを DuckDB の SQL と Python 組合せで計算する関数群（calc_momentum, calc_volatility, calc_value）。
    - データ不足時は None を返す動作や、探索範囲バッファなどを実装。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応）、IC（calc_ic）、ランク付けユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas に依存せず標準ライブラリ + DuckDB のみで設計。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- 環境変数の取り扱いに注意:
  - 必須 API キー類は明示的に _require() で取得（未設定時は ValueError）。
  - OpenAI 利用は関数引数で api_key を注入可能。呼び出し元がキー管理を適切に行うことを想定。
  - .env 自動ロード時に既存 OS 環境変数は保護される（protected set の使用）。

### Notes / Design decisions（重要な実装上の注意）
- ルックアヘッドバイアス対策:
  - すべての分析/スコアリング関数で datetime.today()/date.today() を直接参照しない設計。target_date 引数を基準に過去データのみを参照する。
- フェイルセーフ:
  - AI API 失敗やデータ不足時は致命的例外にせずフォールバック（例: macro_sentiment=0.0、ma200_ratio=1.0、スコア取得失敗はスキップ）する方針。
- テスト容易性:
  - OpenAI 呼び出しなどはモジュール内でラップしており、unittest.mock.patch で差し替え可能。
- DB 書き込みの冪等性:
  - ai_scores / market_regime 等への書き込みは一度 DELETE してから INSERT することで冪等性を確保。トランザクション（BEGIN/COMMIT/ROLLBACK）で整合性を担保。
- DuckDB 互換性:
  - executemany に空リストを渡せない制約を考慮したガードを実装。

### Known issues / TODO
- 一部指標（例: PBR、配当利回り）は未実装（calc_value の注記参照）。
- OpenAI のモデルやレスポンスフォーマットが将来変わった場合の互換性対応（ログ/例外処理はあるが将来的な SDK 変化への追加対応が必要になる可能性あり）。
- ETL の J-Quants クライアント実装（kabusys.data.jquants_client）は本リリースの外部依存として存在する想定。実運用時は認証/レート制限等の調整が必要。

---

（今後のリリースでは Unreleased セクションを用意し、バグ修正・機能追加・破壊的変更を分かりやすく記載します。）