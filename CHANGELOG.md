# CHANGELOG

このプロジェクトの変更履歴は Keep a Changelog の形式に準拠しています。  
セマンティックバージョニングを採用しています。

## [0.1.0] - 2026-04-04

初回公開リリース。本リポジトリに含まれる主要機能と設計上のポイントをまとめます。

### 追加 (Added)
- パッケージ基盤
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として公開。

- 環境設定 / 設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートは `.git` または `pyproject.toml` を基準に探索（CWD に依存しない）。
    - 読み込み優先順: OS 環境変数 > `.env.local` > `.env`。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能。
  - .env パーサは以下に対応：
    - `export KEY=val` 形式、
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理、
    - クォート外のインラインコメント（`#`）の扱い（直前が空白/タブの場合にコメントとみなす）、
    - 無効行・コメント行のスキップ。
  - 重要な環境変数の取得を行う `Settings` クラスを提供（必須変数未設定時は ValueError を送出）。
    - J-Quants / kabu ステーション / LINE API トークン、データベースパス（DuckDB / SQLite）、監視関連ファイルパス・閾値、実行環境種別（development/paper_trading/live）とログレベル検証など。
    - `is_live` / `is_paper` / `is_dev` プロパティによる環境判定。

- AI（ニュース NLP / レジーム検出）
  - ニュースセンチメントスコアリング (`kabusys.ai.news_nlp.score_news`)
    - raw_news / news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信してセンチメントを算出。
    - バッチサイズや1銘柄あたりの最大記事数・文字数制限を導入してトークン肥大化を防止。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実装。
    - レスポンス検証（JSON パース、results の存在、コード照合、スコアの数値性）を行い、安全に ±1.0 にクリップして ai_scores テーブルへ冪等的に保存（DELETE → INSERT）。
    - タイムウィンドウは JST ベースで定義（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して DB クエリに使用）し、ルックアヘッドバイアスを回避。
    - API キーは引数で注入可能（テスト容易性）。未設定時は環境変数 `OPENAI_API_KEY` を参照し、未設定だと ValueError。
  - 市場レジーム判定 (`kabusys.ai.regime_detector.score_regime`)
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出はタイトルベースのキーワードフィルタ（デフォルトで複数キーワードを指定）。
    - OpenAI 呼び出し（gpt-4o-mini、JSON Mode）は堅牢にリトライ実装し、API 失敗時は macro_sentiment=0.0 としてフェイルセーフで継続。
    - レジームスコアはクリップし、結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）する。
    - こちらも API キーは引数あるいは環境変数で供給。

- データ基盤（Data Platform）
  - マーケットカレンダー管理 (`kabusys.data.calendar_management`)
    - JPX カレンダーの夜間バッチ更新ジョブ `calendar_update_job`（J-Quants API からの差分取得 → 保存）を実装。
    - 営業日判定ユーティリティ: `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day` を提供。
    - DB にカレンダー情報がない場合は曜日ベース（土日休み）でフォールバック。
    - バックフィル、先読み、健全性チェック（将来日付が極端に遠い場合はスキップ）等の安全策を実装。
  - ETL パイプライン基盤 (`kabusys.data.pipeline`, `kabusys.data.etl`)
    - ETL 実行結果を格納する `ETLResult` dataclass を公開（取得数 / 保存数 / 品質問題 / エラー等を含む）。
    - ETL の設計方針（差分取得、backfill、品質チェックを継続的に収集し呼び出し元が判断する方式など）を反映したユーティリティ群。
    - DuckDB との互換性や executemany の空リスト回避等、実装上の注意点を考慮。

- リサーチ / ファクター計算 (`kabusys.research`)
  - ファクター計算モジュール `factor_research` を追加。
    - モメンタム（1/3/6 ヶ月リターン、200日MA乖離）、ボラティリティ（20日ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER / ROE）を DuckDB ベースの SQL と Python で実装。
    - 出力は (date, code) をキーとする dict のリスト形式。
    - データ不足時は None を返す設計。
  - 特徴量探索 `feature_exploration` を追加。
    - 将来リターン計算（任意ホライズン）、IC（Spearman のランク相関）計算、統計サマリー、ランク関数等を提供。
    - pandas 等の外部依存を避け、標準ライブラリ + DuckDB のみで実装。
  - 研究用ユーティリティとして `zscore_normalize` を data.stats から re-export。

### 変更 (Changed)
- 初版のため該当なし。

### 修正 (Fixed)
- 初版のため該当なし。

### 既知の制約 / 注意点 (Known issues / Notes)
- OpenAI 呼び出しは gpt-4o-mini および JSON Mode を前提とした実装になっているため、その SDK/API のバージョン差異に注意。
- DuckDB のバインドや executemany の挙動に依存した実装箇所があり、環境によっては調整が必要（特に空リストの executemany を回避する処理を追加済み）。
- いくつかの参照モジュール（例: `kabusys.data.jquants_client`）は本コードで呼び出しているが、ここに含まれていない外部実装に依存する。
- パッケージの __all__ に `strategy`, `execution`, `monitoring` が含まれるが、今回提供されたスナップショットにはそれらの具象実装ファイルが含まれていないため、今後のリリースで実装される想定。

### セキュリティ (Security)
- 環境変数の読み込みに際して OS 環境変数を保護する仕組み（protected set）を採用。
- API キー等の必須情報は明示的にチェックし、未設定時はエラーとして扱う（安全側の設計）。

---

今後のリリース案（予定）
- strategy / execution / monitoring の具体実装追加（実取引 / 発注ロジック / モニタリング）
- jquants_client の組み込み、テストベンチの整備、CI の追加
- 性能・スケーラビリティ改善、より詳細な品質チェックルールの追加

（上記は提供されたコードベースの内容から推測して作成しています。実際の履歴やリリースノートと差分がある場合は差し替えてください。）