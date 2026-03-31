# CHANGELOG

すべての注目すべき変更点を記載します。フォーマットは "Keep a Changelog" に準拠します。

## [0.1.0] - 2026-03-31

最初の公開リリース。

### 追加 (Added)
- パッケージ基本構成
  - パッケージエントリポイントを追加（kabusys.__init__）。
  - 公開サブパッケージ候補として data / research / ai / monitoring / execution / strategy を定義。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を自動読込する仕組みを実装。
    - 読み込み順序: OS 環境 > .env > .env.local（.env.local は上書き）。
    - 自動ロードを無効化するためのフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env パーサを実装（コメント、export プレフィックス、シングル／ダブルクォート、エスケープ対応）。
  - 既存 OS 環境変数を保護するための protected キー概念を実装。
  - Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / 監視閾値 / 環境種別 / ログレベル等）。
    - 必須変数未設定時は ValueError を送出する `_require` を採用。
    - `KABUSYS_ENV` と `LOG_LEVEL` の検証ロジックを追加。
    - DB パス（duckdb/sqlite）や監視用閾値（CPU/Memory/Disk）等の便利プロパティを追加。

- AI モジュール (`kabusys.ai`)
  - ニュースの NLP スコアリング（`kabusys.ai.news_nlp.score_news`）
    - raw_news / news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）へ送信してセンチメントを取得。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたりの最大記事数と文字数を制限（トークン肥大化対策）。
    - JSON Mode のレスポンス検証と復元処理（必要に応じて最外の {} を抽出）。
    - リトライ（429・ネットワーク・タイムアウト・5xx）に対する指数バックオフ。
    - 部分成功時の DB 書き込みロジック（DELETE → INSERT、対象コードのみ置換）で既存データを保護。
    - 時間ウィンドウ計算ユーティリティ（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換）を実装。
    - テスト容易性: API 呼び出しは内部関数で抽象化し unittest.mock.patch で差し替え可能。
  - 市場レジーム判定（`kabusys.ai.regime_detector.score_regime`）
    - 日次での市場レジーム判定を実装（'bull' / 'neutral' / 'bear'）。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成。
    - マクロニュースは news_nlp のウィンドウ計算を利用してタイトルをフィルタ（マクロキーワードリストあり）。
    - OpenAI への呼び出しは独立実装（news_nlp とプライベート関数を共有しない設計）。
    - API エラー・パースエラー時は安全側（macro_sentiment=0.0）で継続するフェイルセーフを実装。
    - 結果は market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で保存。

- データプラットフォーム関連 (`kabusys.data`)
  - カレンダー管理（`kabusys.data.calendar_management`）
    - JPX カレンダーの DB 保持・更新ロジック（nightly job: calendar_update_job）。
    - market_calendar がない場合の曜日ベースフォールバック（週末は非営業日扱い）。
    - next_trading_day / prev_trading_day / is_trading_day / get_trading_days / is_sq_day を提供し、DB 登録値優先かつ未登録日は曜日フォールバックで一貫性を保持。
    - 最大探索日数を設け無限ループを防止（_MAX_SEARCH_DAYS）。
    - カレンダー取得時の健全性チェックとバックフィル処理を実装。
  - ETL パイプライン（`kabusys.data.pipeline` / `kabusys.data.etl`）
    - ETL 実行結果を表す dataclass `ETLResult` を追加（品質チェック結果・エラー集約等を保持）。
    - 差分更新、バックフィル、品質チェック、idempotent 保存（jquants_client の save_* を利用）を想定したインターフェース設計。
    - 内部ユーティリティ（テーブル存在チェック、最大日付取得等）を実装。
    - `kabusys.data.etl` から `ETLResult` を再エクスポート。

- リサーチ / ファクター計算 (`kabusys.research`)
  - ファクター計算（`kabusys.research.factor_research`）
    - モメンタム（1M/3M/6M）、200日移動平均乖離、ATR（20日）、流動性（20日平均売買代金、出来高比率）等を DuckDB SQL で計算する関数を追加:
      - calc_momentum, calc_volatility, calc_value
    - raw_financials と prices_daily のみを参照する安全設計（発注 API へはアクセスしない）。
    - データ不足時の None 扱い、結果は (date, code) をキーとする dict リストで返却。
  - 特徴量探索（`kabusys.research.feature_exploration`）
    - 将来リターン計算（calc_forward_returns）：複数ホライズンを1クエリで取得する実装。
    - IC（Information Coefficient）計算（calc_ic）：ランク相関（Spearman に相当）を実装。
    - ランク変換ユーティリティ（rank）：同順位は平均ランクで処理（丸め誤差対策あり）。
    - 統計サマリー（factor_summary）：count/mean/std/min/max/median を計算。
  - research パッケージエントリポイントで主要ユーティリティを再公開。

### 変更 (Changed)
- 初期リリースのため該当なし。

### 修正 (Fixed)
- 初期リリースのため該当なし（ただし各モジュールでフェイルセーフや例外ハンドリングを強化）。

### セキュリティ／堅牢性関連 (Security / Robustness)
- OpenAI キー未設定時に明示的な ValueError を発生させることで、不正な呼び出しを早期検出。
- OpenAI 呼び出しはリトライとバックオフを実装し、API 障害時に例外を伝播させず安全なデフォルト（0.0）へフォールバックする仕様を採用。
- .env 読み込みで OS 環境変数を上書きしない安全デフォルトと、上書きを制御する protected 機能を実装。
- DuckDB への書き込み時はトランザクション（BEGIN/COMMIT/ROLLBACK）を利用し、ROLLBACK 失敗時は警告ログを残す実装。

### 既知の制約・注意点 (Known issues / Notes)
- OpenAI API（gpt-4o-mini）を利用するため、API キー（OPENAI_API_KEY）が必要。未設定時は該当関数が ValueError を送出する。
- news_nlp と regime_detector は JSON モードでの厳密な出力を期待しているが、実際のモデル応答が完全な JSON でないケースに備え復元ロジックを実装している。ただし完全な健全性を保証するものではない。
- DuckDB に対する executemany の空リストバインドに関する互換性問題を考慮して、空チェックを行ってから executemany を呼ぶ実装にしている。
- calendar_update_job / ETL 周りは jquants_client の具象実装に依存するため、外部 API の挙動により実行結果が左右される。

---

その他、各モジュールには詳細な docstring が含まれており、処理フロー・設計方針・境界条件について説明しています。今後のリリースではテストカバレッジの強化、API クライアント抽象化、monitoring / execution / strategy の実装拡充を予定しています。