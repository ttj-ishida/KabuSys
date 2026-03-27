# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
初回リリース（v0.1.0）の内容をコードベースから推測してまとめています。

全般
- リリース日: 2026-03-27
- バージョン: 0.1.0

## [0.1.0] - 2026-03-27

### 追加
- パッケージの初期構成を追加
  - パッケージ名: kabusys（__version__ = "0.1.0"）
  - top-level export: data, strategy, execution, monitoring（__all__）

- 設定 / 環境変数管理 (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルート検出ロジックを含む）
  - .env/.env.local の優先順位と OS 環境変数保護（protected set）に対応
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能
  - 複雑な .env 行パース実装（export プレフィックス、引用符付き文字列、インラインコメント取り扱い）
  - Settings クラスを実装し、次のプロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL 検証
    - is_live / is_paper / is_dev の便宜プロパティ
  - 必須環境変数未設定時は ValueError を送出する _require 関数を提供

- AI モジュール (`kabusys.ai`)
  - ニュース NLP スコアリング (`news_nlp.score_news`)
    - raw_news, news_symbols から銘柄別に記事を集約して OpenAI（gpt-4o-mini）にバッチ送信し、ai_scores に書き込み
    - 時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供
    - 銘柄チャンク処理（デフォルト最大 20 銘柄／APIコール）
    - トークン肥大対策（1 銘柄あたり最大記事数・最大文字数でトリム）
    - JSON mode のレスポンス検証と堅牢なパース（前後余分テキストの復元ロジック含む）
    - ±1.0 でのクリップ、Retry（429/ネットワーク/タイムアウト/5xx）を実装
    - 部分成功を許す idempotent な DB 上書き戦略（DELETE → INSERT、影響銘柄を絞る）
    - APIキー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）
  - 市場レジーム判定 (`regime_detector.score_regime`)
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して 'bull'/'neutral'/'bear' を判定
    - マクロ記事フィルタリング（キーワードリスト）と OpenAI 呼び出しで macro_sentiment を算出
    - LLM 呼び出しのリトライ／フォールバック（API失敗時 macro_sentiment=0.0）
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）で market_regime に保存
    - datetime.today() 等を参照しない設計（ルックアヘッドバイアス対策）
    - API 呼び出しは内部で OpenAI クライアントを生成し、api_key を注入可能

- データプラットフォーム / ETL (`kabusys.data`)
  - ETL インターフェースの公開（ETLResult を再エクスポート）
  - ETL パイプライン (`data.pipeline`)
    - 差分更新、バックフィル、品質チェックを考慮した ETLResult データクラスを実装
    - DuckDB を利用した最終日取得ユーティリティ、テーブル存在チェック、結果の集約・エラーハンドリング
    - ETL 実行結果の辞書化（品質問題を (check_name, severity, message) に変換）
  - マーケットカレンダー管理 (`data.calendar_management`)
    - market_calendar を基にした営業日判定 API を提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジック
    - カレンダー夜間更新ジョブ calendar_update_job（J-Quants から差分取得・バックフィル・健全性チェック）
    - DB テーブルの存在チェックや日付変換ユーティリティを実装
    - 最大探索日数(_MAX_SEARCH_DAYS) 等の安全ガードを導入

- リサーチ / ファクター処理 (`kabusys.research`)
  - factor_research.py
    - モメンタム（1M/3M/6M リターン、200日MA乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER、ROE）を DuckDB 上で計算する関数を実装:
      - calc_momentum, calc_volatility, calc_value
    - スキャン範囲のバッファやデータ不足時の None 返却など実運用を想定した設計
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）: 任意ホライズンのリターンを LEAD を使って一括取得
    - IC（Information Coefficient）計算（calc_ic）: Spearman（ランク相関）実装、データ不足時は None を返す
    - ランキングユーティリティ（rank）: 同順位は平均ランク（丸め処理で ties を安定検出）
    - ファクター統計サマリー（factor_summary）: count/mean/std/min/max/median を算出
  - data.stats との連携（zscore_normalize を再エクスポート）

### 改善（設計上の決定／堅牢性）
- LLM 呼び出しに対して共通の堅牢性対策を導入:
  - JSON レスポンスの厳密検証、パース失敗は警告ログを出しフェイルセーフにフォールバック（例: macro_sentiment=0.0）
  - リトライポリシー（指数バックオフ）と 5xx 判定の扱いを定義
  - テストのために _call_openai_api を patch 可能に設計（ユニットテスト容易化）
- ルックアヘッドバイアス防止:
  - 各モジュールで datetime.today()/date.today() を直接参照しない設計（target_date を明示的に引数で渡す）
  - ニュース・価格取得クエリは target_date を境界に排他条件を付与
- DB 書き込みは冪等・部分失敗耐性を重視:
  - ai_scores / market_regime などで DELETE→INSERT 方式を採用し、影響範囲を限定して既存データを不要に消さない
  - DuckDB の executemany の制約を考慮した空リストチェック

### 既知の制限 / 注意点
- OpenAI API（gpt-4o-mini）への依存があり、APIキーの設定が必須な処理（score_news, score_regime）はキー未設定時に ValueError を送出する
- DuckDB に依存するテーブルスキーマ（prices_daily, raw_news, news_symbols, raw_financials, market_calendar 等）が前提。初期データやスキーマが整っていないと関数は期待通り動作しない
- 一部モジュールは jquants_client や quality モジュールを呼び出す実装（外部 API クライアント・品質チェックロジックは別途実装が必要）

### セキュリティ
- 設定読み込み時に OS 環境変数を保護する仕組み（読み込み時の protected set）を導入
- APIキーは明示的に引数で注入可能にしてテスト時のモックやインジェクションを容易化

---

今後の予定（推測）
- strategy / execution / monitoring の具象実装（現状は top-level に空のエクスポートがあるのみ）
- jquants_client / quality 等外部依存モジュールの詳細実装・テスト補完
- ドキュメント（使い方、スキーマ定義、DB 初期化手順）の整備

（注）この CHANGELOG は提供されたソースコードから意図・挙動を推測して作成しています。リリースノートの正式版は実際の変更履歴／コミットログに基づいて作成してください。