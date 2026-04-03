# Changelog

すべての注目すべき変更をここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

## [0.1.0] - initial release
最初の公開バージョン。日本株自動売買システム「KabuSys」のコア機能群を実装しています。

### 追加 (Added)
- パッケージ基盤
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。公開サブパッケージ: data, strategy, execution, monitoring。
  - バージョン番号を 0.1.0 に設定。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出（.git または pyproject.toml を探索）により CWD に依存しない自動ロード。
  - .env/.env.local の読み込み順序と上書きルールを実装（OS 環境変数は保護）。
  - export KEY=val 形式やクォート・エスケープ、インラインコメントに対応した独自の .env パーサを実装。
  - オートロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供（属性アクセスで各種設定を取得）。
    - J-Quants / kabuステーション / LINE / DB パス / 監視関連 / システム設定等のプロパティを実装。
  - 環境値バリデーション: KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL（DEBUG/INFO/...）の妥当性チェック。
  - 必須環境変数未設定時は ValueError を投げる _require ヘルパを用意（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。

- AI（ニュースNLP / 市場レジーム判定）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - JST ベースのニュース収集ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を実装（calc_news_window）。
    - 1チャンクあたり最大 20 銘柄、1銘柄あたり記事数/文字数上限（トリム）を実装。
    - JSON Mode を前提にレスポンス検証を実装（JSON 抽出 / results 構造 / code・score の型チェック）。
    - DuckDB 0.10 の executemany の制約を考慮し、部分置換（DELETE → INSERT）で冪等的に ai_scores を更新。
    - リトライ戦略: 429/ネットワーク/タイムアウト/5xx は指数バックオフで再試行。その他エラーはスキップし処理継続。
    - テスト容易性: _call_openai_api を patch して差し替え可能に設計。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225 連動型）の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を組み合わせて日次レジーム（bull/neutral/bear）を判定。
    - OpenAI 呼び出しは独立実装、API 失敗時はフォールバック macro_sentiment=0.0 としてフェイルセーフ動作を実装。
    - レジーム結果は market_regime テーブルに冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - ルックアヘッドバイアス対策: target_date 未満のデータのみ参照し、datetime.today()/date.today() を直接参照しない設計。

- データ（Data Platform）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを用いた営業日判定 API を提供。
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - DB にデータがない場合は曜日ベース（平日のみ営業日）でフォールバックする一貫した挙動。
    - JPX カレンダー差分取得のバッチジョブ calendar_update_job を実装（J-Quants クライアント経由）。バックフィル・健全性チェックを実装。
  - ETL / パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを実装（取得数、保存数、品質問題、エラー等を集約）。
    - 差分更新・バックフィル・品質チェック統合を想定した ETL パイプライン設計（jquants_client / quality を利用）。
    - etl モジュールの公開インターフェースとして ETLResult を再エクスポート。

- Research（因子研究）（src/kabusys/research/*）
  - factor_research.py
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR）、Value（PER / ROE）等の計算関数を実装。
    - DuckDB SQL を用いて効率的に計算。結果は (date, code) をキーとした dict のリストとして返す。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
    - 外部依存を持たず、標準ライブラリのみで統計処理を実装。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### セキュリティ (Security)
- 環境変数や API キーの取り扱いに注意:
  - OpenAI API キーは OPENAI_API_KEY 環境変数または各 API 呼び出しの api_key 引数で提供する必要がある（未設定時は ValueError）。
  - J-Quants / kabu ステーション用の機密情報はそれぞれ JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等の環境変数で管理。
  - .env 自動読み込みはプロジェクトルート検出に依存し、必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できる。

### 既知の制約・注意事項 (Notes)
- DuckDB 互換性:
  - executemany に空リストを渡せない等、DuckDB（特に 0.10 系）に依存したワークアラウンドを実装している箇所がある（ai_scores 書き込み等）。
- ルックアヘッドバイアス防止:
  - 全てのバッチ処理・スコアリング関数は内部で datetime.today()/date.today() を直接参照せず、target_date ベースで動作する設計。
- OpenAI 呼び出し:
  - gpt-4o-mini を想定。API レスポンスは JSON Mode（response_format）を利用しており、パースの失敗や API 障害はフェイルセーフでスコア 0.0 やスキップにフォールバックすることがある。
  - テストや CI のために各モジュール内の _call_openai_api をモック可能にしている。
- テーブルスキーマ:
  - 本リリースで参照・更新するテーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など）は事前に適切なスキーマで用意しておく必要がある。
- ロギング:
  - 各モジュールは logging を利用して詳細な情報・警告を出力する。LOG_LEVEL は Settings.log_level で制御。

もしリリースノートに特定の変更点（例: バグ修正、追加機能の詳細なドキュメント化、マイグレーション手順）を追記したい場合は、変更のあったファイル名・関数名・期待する動作・互換性への影響を教えてください。