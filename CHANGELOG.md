# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

※このCHANGELOGはリポジトリ内のコード（モジュール、関数、実装のコメント等）から推測して作成した初期リリース向けの記載です。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回公開リリース。

### 追加 (Added)
- パッケージ基礎
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。  
  - パッケージ公開 API を定義（data, strategy, execution, monitoring）。

- 設定管理 (kabusys.config)
  - .env および環境変数から設定を安全に読み込む自動ロード機能を実装。
  - プロジェクトルート判定ロジックを実装（.git または pyproject.toml を探索）し、CWD に依存しない自動ロードを実現。
  - .env のパースを強化:
    - コメント行 / 空行を無視。
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープに対応。
    - クォートなし値の行内コメント処理を改善。
  - .env と .env.local の読み込み順序を実装（OS 環境 > .env.local > .env）。.env.local は上書き (override)。
  - OS 環境変数を保護する protected キー群を導入して誤上書きを防止。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（テスト用途）。
  - 必須環境変数取得ヘルパー _require と Settings クラスを提供。取得可能な設定例:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV (development / paper_trading / live) と LOG_LEVEL の検証
    - is_live / is_paper / is_dev のプロパティ

- AI モジュール (kabusys.ai)
  - news_nlp.score_news:
    - raw_news と news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを評価。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を提供（calc_news_window）。
    - バッチ処理（最大20銘柄）での API 呼び出し、トークン肥大化対策（記事数・文字数制限）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフとリトライを実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results リスト検証、未知コード無視、数値チェック）。
    - DuckDB へ冪等的に書き込む処理（DELETE → INSERT、部分失敗時に既存データを保護）。
    - DuckDB 互換性に配慮（executemany に空リストを渡さないガード）。
  - regime_detector.score_regime:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ保存。
    - MA 計算は target_date 未満のデータのみを参照し、ルックアヘッドバイアスを排除。
    - マクロニュース抽出（マクロキーワード群に一致するタイトルを最大件数取得）。
    - OpenAI 呼び出し（独立した実装）とリトライ/フォールバック（API 失敗時は macro_sentiment=0.0）。
    - DB 書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で行い、エラー時には ROLLBACK を実行。

- データ管理 (kabusys.data)
  - calendar_management:
    - JPX マーケットカレンダー管理機能を実装（market_calendar を基に営業日判定、next/prev/get_trading_days、is_sq_day）。
    - データ未取得時は曜日ベースでのフォールバック（週末を非営業日扱い）。
    - 最大探索日数の上限を設け、無限ループを防止。
    - カレンダー夜間バッチ（calendar_update_job）を実装。J-Quants API から差分取得し冪等的に保存、バックフィルと健全性チェックを実装。
  - pipeline / etl:
    - ETLResult データクラスを公開（etl/pipeline 間での結果伝搬に利用）。
    - ETL パイプライン設計に従った差分更新、バックフィル、品質チェック（quality モジュール連携）を想定したユーティリティを実装の骨子として用意。
    - internal ユーティリティ関数（テーブル存在確認、最大日付取得、トレーディングデイ補正など）を実装。

- リサーチ (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER, ROE）を DuckDB ベースで計算する関数を実装（calc_momentum / calc_volatility / calc_value）。
    - 計算は prices_daily / raw_financials テーブルのみを参照。結果は (date, code) をキーとする辞書のリストで返却。
    - データ不足時は None を返す挙動を明確化。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）を実装。任意ホライズン（デフォルト [1,5,21]）に対応。
    - IC（Information Coefficient、スピアマンの順位相関）計算（calc_ic）とランク変換ユーティリティ (rank) を実装。
    - ファクター統計サマリー生成（factor_summary）を実装。外部依存を持たない標準ライブラリ実装。

### 変更 (Changed)
- リポジトリ構成 / モジュール間の分離方針を明確化:
  - OpenAI API 呼び出しは各モジュール内で独立実装し、モジュール間でプライベート関数を共有しない設計（テスト時に各モジュールごとに差し替え可能）。
  - すべての処理で datetime.today() / date.today() の直接参照を避け、入力の target_date を明示的に受け取ることでルックアヘッドバイアスを防止。

### 修正 (Fixed)
- API 呼び出し失敗時のフェイルセーフ動作を統一:
  - news_nlp/regime_detector では OpenAI API の失敗（レート制限、ネットワーク、タイムアウト、5xx）時に適切にログを出力し、フェイルセーフ値（スコア 0.0 など）にフォールバックするよう実装。
- DuckDB 向けの互換性対策:
  - executemany に空リストを渡すと失敗するバージョンを考慮し、空リスト時は実行をスキップするガードを追加。

### セキュリティ (Security)
- API キーの取り扱い:
  - OpenAI キーは引数で注入可能（テスト容易性）かつ環境変数 OPENAI_API_KEY から参照。未設定時は ValueError を送出して明示的にハンドリング。
  - 環境変数読み込み時に OS 環境を保護する仕組み（protected set）を実装し、重要なキーが意図せず上書きされるのを防止。

### 注意事項 / 備考
- 多くの処理は DuckDB 上の特定テーブル（prices_daily, raw_news, news_symbols, ai_scores, raw_financials, market_regime, market_calendar など）に依存します。これらが存在しない場合やデータ不足の場合は関数が None や 0 を返す、またはログを出力して安全に終了します。
- OpenAI のレスポンスは JSON mode を想定していますが、余分な前後文字列が混入するケースを考慮した復元処理を実装しています。
- .env の自動読み込みは配布後の挙動にも配慮しており、プロジェクトルート探索により実行コンテキストに依存しない動作を目指しています。

---

（今後のリリースでは各モジュールの改修点、パフォーマンス改善、API 仕様変更、DB スキーマ更新などを個別に記載してください。）