# CHANGELOG

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」形式に準拠します。  
初期リリース相当のコードベースから機能・設計意図・注意点をコード内容より推測して記載しています。

なお、本リリースではセマンティックバージョニングに従い version 0.1.0 を設定しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-04

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを公開。__version__ = 0.1.0、公開モジュール: data, strategy, execution, monitoring をエクスポート。
- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートは __file__ を基点に `.git` または `pyproject.toml` を探索して特定（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を用意（テスト向け）。
    - .env のパースは export 構文、クォート内のエスケープ、インラインコメントなどを考慮。
  - Settings クラスを提供し、J-Quants / kabu / LINE / DB /監視 / ログ関連の設定プロパティを公開。
    - 必須環境変数未設定時は明示的に ValueError を送出するユーティリティを用意。
    - 環境変数検証: KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL の検証を実装。
- AI ベースのニュース解析 (kabusys.ai)
  - news_nlp モジュール: raw_news を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント(ai_score) を ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリで利用）。
    - バッチサイズ・文字数・記事数の上限を設定してトークン肥大化を抑制。
    - レート制限・ネットワーク断・タイムアウト・5xx を対象に指数バックオフでリトライ。
    - レスポンスは JSON Mode 想定。パース・バリデーションを厳格に行い、未知コードは無視、スコアは ±1.0 にクリップ。
    - API 呼び出し部分はテストしやすいように _call_openai_api を分離（unittest.mock.patch による差替え想定）。
    - 部分失敗に備え、書き込み前に対象コードのみ DELETE してから INSERT する冪等保存を行う（DuckDB 互換性を考慮）。
  - regime_detector モジュール: ETF 1321（日本225連動）の 200 日移動平均乖離（重み70%）とニュースの LLM センチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を日次で判定・market_regime テーブルへ保存。
    - ma200_ratio の計算は target_date 未満のデータのみ使用（ルックアヘッド防止）。
    - マクロニュースはキーワードフィルタで抽出し、最大記事数を制限。記事無しなら LLM 呼び出しをスキップ。
    - LLM 呼び出しはリトライ/フォールバック実装。API 失敗時は macro_sentiment = 0.0 として継続（フェイルセーフ）。
    - DB 書込みは BEGIN/DELETE/INSERT/COMMIT で冪等化。失敗時は ROLLBACK を試行。
- データプラットフォーム (kabusys.data)
  - calendar_management:
    - market_calendar テーブルの有無を考慮した営業日判定 API を提供（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB に登録があればその値を優先し、未登録日は曜日ベース（土日除外）でフォールバック。
    - 夜間バッチ calendar_update_job を実装し、J-Quants から差分取得 → 保存（バックフィル／健全性チェックあり）を行う。
  - pipeline / ETL:
    - ETLResult データクラスを公開（ETL の収集結果・品質問題・エラー集約に利用）。
    - 差分更新・保存・品質チェックの実装方針を反映（backfill, カレンダー先読み等）。
    - DuckDB でのテーブル存在チェックや最大日付取得等のユーティリティを実装。
  - ETL 公開インターフェースを etl モジュールで再エクスポート（ETLResult）。
- リサーチ機能 (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比）、バリュー（PER, ROE）を DuckDB + SQL で計算する関数を実装。
    - すべて prices_daily / raw_financials を参照。結果は (date, code) を含む辞書のリストで返す。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）／ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
    - 外部依存を避け、標準ライブラリのみで Spearman ランク相関や統計量を計算。
- テスト・設計上の配慮
  - LLM 呼び出し関数をモジュール内で分離しモック可能にしてユニットテストを容易にしている。
  - datetime.today()/date.today() をスコア計算ロジックの内部で直接参照しない設計（ルックアヘッドバイアス防止）。
  - DuckDB バージョン差異への配慮（executemany の空パラメータ不可など）をコメント・実装に反映。

### 変更 (Changed)
- （初期リリースのため該当なし）

### 修正 (Fixed)
- （初期リリースのため該当なし）

### 注意事項 / 補足 (Notes)
- OpenAI API
  - news_nlp / regime_detector / score系の公開関数は OpenAI API キーを要求する（api_key 引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError を送出する。
  - OpenAI 呼び出しは gpt-4o-mini と JSON mode を想定。
- 環境変数自動ロード
  - プロジェクトルートが発見できない場合 (.git / pyproject.toml がない) 自動ロードはスキップされる。
  - OS 環境変数はデフォルトで保護され、.env/.env.local の上書きから除外される。
- データベース（DuckDB）用留意点
  - 一部実装は DuckDB の特性（executemany の挙動、日付型の取り扱い等）に依存しており、異なるバージョンでの挙動差に注意。
- フェイルセーフ方針
  - 外部 API の失敗は可能な範囲でフェイルセーフ（スコア 0.0 など）とし、処理継続を優先する設計。
- ルックアヘッドバイアス防止
  - 重要な分析/スコアリングロジックは target_date 引数を明示的に受け、現日時参照を避けることでバックテストの再現性を高めている。

---

（記載はコード内ドキュメント文字列・実装内容から推測して作成しました。実際のリリースノートとして公開する際は、リポジトリのコミット履歴やリリース差分を基に追記・修正してください。）