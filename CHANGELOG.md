# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-03-27

### Added
- 初回リリース: KabuSys — 日本株自動売買システムのコアライブラリを追加。
  - パッケージエントリポイント: `kabusys.__version__ = "0.1.0"`。公開モジュールとして `data`, `strategy`, `execution`, `monitoring` をエクスポート。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ローダを実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能（テスト用途）。
    - プロジェクトルート判定は `__file__` を起点に `.git` または `pyproject.toml` を探索して決定（CWD に依存しない）。
  - .env パーサの強化:
    - `export KEY=value` 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。
    - クォートなしの行でのインラインコメント扱いを適切に処理。
  - `Settings` クラスを提供し、以下などの設定をプロパティ経由で取得:
    - J-Quants / kabu API / Slack トークン・チャンネル
    - DB パス設定（DuckDB / SQLite のデフォルトパス）
    - 環境種別 (`KABUSYS_ENV`) とログレベル検証（許容値検証）
    - ヘルパー: `is_live`, `is_paper`, `is_dev`
  - 必須環境変数未設定時は明示的に `ValueError` を送出する。

- AI モジュール（自然言語処理・レジーム判定）
  - `kabusys.ai.news_nlp`
    - score_news(conn, target_date, api_key=None)
      - 指定タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）に基づくニュース集約。
      - 銘柄ごとに記事を結合・トリムし、OpenAI（gpt-4o-mini）へバッチ送信（1リクエスト最大 20 銘柄）。
      - リトライ（429・ネットワーク・タイムアウト・5xx）を指数バックオフで実施。
      - レスポンスのバリデーション（JSON 抽出・キー/型チェック・スコアの有限性チェック）。
      - スコアを ±1.0 にクリップして `ai_scores` テーブルへ冪等的に書き込む（対象コードのみ DELETE → INSERT、部分失敗に配慮）。
      - API キー未指定時は `ValueError` を送出。
    - `calc_news_window(target_date)` を提供（UTC naive datetime でウィンドウを返す）。
    - テスト容易性のため OpenAI 呼び出し箇所をパッチ可能に設計（`_call_openai_api` を差し替え可能）。
  - `kabusys.ai.regime_detector`
    - score_regime(conn, target_date, api_key=None)
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
      - MA200 計算は target_date 未満のデータのみ使用し、データ不足時は中立（1.0）でフェイルセーフ。
      - マクロニュース抽出はキーワードベースで最大件数を取得し、OpenAI で JSON 出力を要求してセンチメントを得る。API エラー時は macro_sentiment=0.0 にフォールバック。
      - 合成スコアをクリップし、`market_regime` テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK 後に例外を伝播。

- データ処理モジュール（DuckDB ベース）
  - `kabusys.data.calendar_management`
    - 市場カレンダー管理と営業日ロジックを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - カレンダーデータ未取得時は曜日ベースのフォールバック（平日のみ営業日）。
    - 最大探索範囲の上限や健全性チェック（将来日付が異常に遠い場合など）を実装。
    - 夜間バッチ `calendar_update_job(conn, lookahead_days=90)` を実装し、J-Quants クライアント経由で差分取得 → 冪等保存（バックフィル考慮、エラーハンドリング）。
  - `kabusys.data.pipeline` / `kabusys.data.etl`
    - ETL パイプラインに関連するユーティリティと結果クラス `ETLResult` を提供。
    - ETL 構成: 差分更新、IDempotent 保存、品質チェックの結果収集（重大度情報含む）、バックフィルの取り込み。
    - `ETLResult` は処理統計・品質問題・エラーを格納し、辞書化メソッドを提供。
    - DuckDB の互換性（テーブル存在チェック、空テーブル扱い等）に配慮した実装。

- リサーチ / ファクター分析モジュール
  - `kabusys.research.factor_research`
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、ma200 乖離を計算（データ不足時は None を返す）。
    - calc_volatility(conn, target_date): 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算（データ不足時は None）。
    - calc_value(conn, target_date): raw_financials から EPS/ROE を取得し PER/ROE を算出（EPS 0 または欠損は None）。
    - いずれも DuckDB の SQL を主体に実装し、外部 API にはアクセスしない。
  - `kabusys.research.feature_exploration`
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（デフォルト [1,5,21]）を計算。
    - calc_ic(factor_records, forward_records, factor_col, return_col): Spearman（ランク）相関で IC を算出（有効レコードが 3 未満なら None）。
    - rank(values): 同順位は平均ランクを返すランク関数（丸めにより ties を安定化）。
    - factor_summary(records, columns): count/mean/std/min/max/median を返す統計サマリー。
    - 標準ライブラリのみで実装（pandas 等の依存なし）。

### Changed
- （新規リリースのため該当なし）

### Fixed
- （新規リリースのため該当なし）

### Notes / 設計上の重要点
- ルックアヘッドバイアス対策:
  - 日時参照は基本的に外部から渡された `target_date` を利用し、`datetime.today()` / `date.today()` の無秩序な利用を避ける設計を徹底。
- フェイルセーフ挙動:
  - 外部 API（OpenAI 等）障害時は可能な限り処理を継続し（ゼロスコアやスキップ）、致命的な例外は明示的に伝播する。
- 冪等性・部分失敗対策:
  - DB 書き込みは既存レコードを削除してから挿入する等、冪等な更新を行い、部分失敗時に既存データを不必要に消さない手法を採用。
- テスト容易性:
  - OpenAI 呼び出し等外部依存部は内部関数を通しており、ユニットテストで差し替え可能（モックパッチを想定）。
- DuckDB 互換性:
  - `executemany` へ空パラメータを渡さない等、DuckDB 特有の制約に配慮した実装。

### Known limitations / TODO
- OpenAI 関連: API キーは必須。キー未指定時は ValueError。API コスト・レイテンシについての運用考慮が必要。
- 一部外部クライアント（例: jquants_client）の実装は本リリースに依存するが、ここでは参照のみ（実装と統合が必要）。
- strategy / execution / monitoring モジュールの詳細は今後のリリースで拡充予定。

---

（備考）上記はコードコメント・ドキュメント文字列から推測してまとめた初期リリースの変更履歴です。実際のリリースノートとして利用する場合は、リリース日・対象バージョン・外部依存のバージョン等を適宜補完してください。