# CHANGELOG

このファイルは「Keep a Changelog」形式に準拠しています。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-04-01
初回リリース。本パッケージは日本株のデータ取得・ETL・研究（リサーチ）・AIベースのニュース解析・市場レジーム判定・カレンダー管理を行うための基盤的モジュール群を提供します。

### 追加（Added）
- パッケージ基盤
  - kabusys パッケージ初版を追加。__version__ = "0.1.0"。
  - 公開サブパッケージ: data, research, ai, monitoring, strategy, execution（__all__ に記載）。

- 設定管理（kabusys.config）
  - .env / .env.local 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env ファイルの柔軟なパース実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープを考慮）。
  - OS 環境変数の保護（.env 読み込み時に既存キーを保護する protected 機構）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供し、アプリケーションで必要な設定をプロパティ経由で取得可能：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH、PID_FILE_PATH 等
    - CPU/MEMORY/DISK のしきい値
    - KABUSYS_ENV（development / paper_trading / live の検証）、LOG_LEVEL の検証
    - is_live/is_paper/is_dev のユーティリティプロパティ

- AI: ニュースNLP（kabusys.ai.news_nlp）
  - score_news(conn, target_date, api_key=None)
    - raw_news と news_symbols を用いて銘柄別に記事を集約し、OpenAI（gpt-4o-mini）でセンチメントスコアを取得して ai_scores テーブルへ書き込む。
    - タイムウィンドウ計算（JST 基準: 前日 15:00 ～ 当日 08:30、内部は UTC naive datetime に変換）。
    - バッチ処理（1 API コールで最大 20 銘柄）、1 銘柄あたりの記事数／文字数制限（上限でトリム）。
    - OpenAI 呼び出しのリトライ（429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ）。
    - レスポンスの厳格なバリデーション（JSON 抽出、results 配列、code と score の検証、数値チェック、±1.0 クリップ）。
    - 部分成功時の冪等的 DB 書き換え（対象コードのみ DELETE → INSERT）により既存スコアの保護。

- AI: 市場レジーム判定（kabusys.ai.regime_detector）
  - score_regime(conn, target_date, api_key=None)
    - ETF 1321 の 200 日移動平均乖離（ma200_ratio）とマクロニュースの LLM センチメントを合成し、market_regime テーブルへ冪等書き込み。
    - ma200_ratio は target_date 未満のデータのみを使用（ルックアヘッド防止）。データ不足時は中立値 1.0 を使用。
    - マクロニュース抽出はキーワードマッチ（複数キーワード）で上位 N 件を取得。
    - OpenAI 呼び出しは専用のリトライ/フェイルセーフ処理を備え、失敗時は macro_sentiment=0.0 で継続。
    - 出力: regime_score を閾値で判定し regime_label を決定（bull/neutral/bear）。

- 研究（Research）モジュール（kabusys.research）
  - factor_research:
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200日 MA 乖離の算出。データ不足時は None を返す振る舞い。
    - calc_volatility(conn, target_date): 20日 ATR、相対 ATR、20日平均売買代金、出来高比を計算。NULL/不完全データ考慮。
    - calc_value(conn, target_date): raw_financials を参照して PER（EPS が 0/欠損時は None）、ROE を計算。
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons=None): 翌日/翌週/翌月（デフォルト）などの将来リターンを一括 SQL クエリで計算。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関（IC）計算（検証、最小データ数チェック）。
    - rank(values): 同順位は平均ランクにする実装（丸めで ties 検出の安定化）。
    - factor_summary(records, columns): count/mean/std/min/max/median を算出する統計サマリー。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - 市場カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティ:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB 内データ優先、未登録日は曜日ベースのフォールバック（週末除外）。探索範囲上限を設けて無限ループ回避。
    - calendar_update_job(conn, lookahead_days=90): J-Quants から差分取得して market_calendar を冪等的に更新。バックフィルや健全性チェックを実装。
  - pipeline / etl:
    - ETLResult データクラスを公開（ETL の各種メトリクス、品質チェック結果、エラー一覧を格納）。
    - ETL パイプラインの設計方針・ユーティリティ（差分更新、バックフィル、品質チェックの扱い等）を実装。

- 基本設計上の配慮
  - すべての「日付基準」ロジックが datetime.today()/date.today() を内部参照しない設計（ルックアヘッドバイアス回避）。
  - OpenAI など外部 API 呼び出しはリトライ・フォールバックを実装し、原則として例外で処理を止めない（フェイルセーフ）。
  - DuckDB を用いた一括 SQL での計算によりパフォーマンスと単純さを両立。
  - OpenAI の呼び出しは JSON mode（response_format）を利用し、厳格な応答検証を行う設計。
  - テスト容易性のため、OpenAI 呼び出し箇所は内部関数として分離してあり unittest.mock.patch で差し替え可能。

### 変更（Changed）
- 初回リリースのため該当なし。

### 修正（Fixed）
- 初回リリースのため該当なし。

### 既知の問題（Known issues / Notes）
- pipeline.py の末尾付近に _get_max_date 関数の戻り処理が途中で切れているように見える（現状のスニペットでは "return date.fro" のような不完全なコードが存在）。ビルド・実行時に SyntaxError/NameError を引き起こす可能性があります。想定される修正例:
  - row[0] の値が date ならそのまま返し、それ以外は date.fromisoformat(str(val)) 等で変換して返す実装に修正する。
- OpenAI 連携箇所は実際の API キーとクォータ制限に依存するため、本番稼働前にモックを用いたテストとレート制御の確認を推奨。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、該当箇所で空チェックを実装している（現実際の運用では DuckDB バージョン互換性の確認を推奨）。

### 必要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- SLACK_BOT_TOKEN（必須）
- SLACK_CHANNEL_ID（必須）
- OPENAI_API_KEY（news_nlp / regime_detector 利用時に必須）
- その他: DUCKDB_PATH / SQLITE_PATH / PID_FILE_PATH / KABUSYS_ENV / LOG_LEVEL

---

もしご希望であれば、次の作業案を提案できます:
- 既知の問題（pipeline.py の不完全実装）に対する具体的なパッチを作成する。
- README または導入手順（環境変数一覧、DB スキーマ、最小実行例）を作成する。
- CHANGELOG に Unreleased セクションを運用するためのテンプレート化（将来の変更履歴運用ルール）。