# CHANGELOG

すべての注目すべき変更はここに記載します。  
このファイルは「Keep a Changelog」形式に従っています。

最新: Unreleased
=================

[Unreleased]
------------

（現時点で保留中の変更はありません）

0.1.0 - 2026-04-04
-----------------

追加
  - パッケージ初回リリース: kabusys v0.1.0
    - パッケージメタ:
      - __version__ = "0.1.0"
      - パッケージ公開 API: kabusys.__all__ = ["data", "strategy", "execution", "monitoring"]

  - 環境設定 / 設定管理 (kabusys.config)
    - .env ファイルまたは環境変数から設定を読み込む自動ローダを実装
      - 読み込み優先順位: OS環境変数 > .env.local > .env
      - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
      - プロジェクトルート判定は __file__ を起点に .git または pyproject.toml を探索（CWD に依存しない実装）
    - .env 解析の強化:
      - `export KEY=val` 形式に対応
      - シングル/ダブルクォート内のバックスラッシュエスケープを正しく解釈
      - クォートなしの行でのインラインコメントを安全に扱うロジック
    - 環境変数取得ユーティリティ:
      - 必須変数チェック関数 `_require`（未設定時に ValueError を送出）
      - Settings クラスを提供（プロパティ経由で各種設定を取得）
      - 設定例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, DUCKDB_PATH, PID_FILE_PATH 等
      - 環境値バリデーション:
        - KABUSYS_ENV は development/paper_trading/live のみ有効
        - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のみ有効

  - AI モジュール (kabusys.ai)
    - news_nlp: ニュース文章のセンチメントスコアリング
      - raw_news / news_symbols を集約して銘柄ごとのテキストを作成
      - タイムウィンドウ: JST 前日15:00 〜 当日08:30（内部は UTC naive datetime）
      - OpenAI（gpt-4o-mini）へのバッチ送信を実装（1コール最大20銘柄）
      - 1銘柄あたり記事数上限・文字数上限でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）
      - JSON Mode を利用した厳密な出力を期待しつつ、出力前後の余分なテキストが混ざる場合の復元処理を実装
      - レスポンス検証: results 配列・code/score の存在、未知コードの無視、数値への正規化、値の有限性検査
      - スコアクリップ: ±1.0
      - 再試行 (exponential backoff) 実装:
        - 対象: 429 / ネットワーク断 / タイムアウト / 5xx
        - リトライ回数制御と待機時間増加
      - フェイルセーフ設計: API 失敗時は該当チャンクをスキップし、全体の処理継続
      - DuckDB への書き込みは冪等 (DELETE → INSERT) を行い、部分失敗時に他コードの既存データを保護
      - テスト容易性: OpenAI 呼び出し部分は差し替え可能（_call_openai_api を patch 可能）
      - 返り値: 書き込んだ銘柄数

    - regime_detector: 市場レジーム判定
      - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して
        市場レジーム（"bull" / "neutral" / "bear"）を算出
      - ma200_ratio の計算は target_date 未満のデータのみを参照し、ルックアヘッドバイアスを防止
      - マクロニュースは news_nlp の calc_news_window で算出されるウィンドウから抽出
      - OpenAI（gpt-4o-mini）を用いて JSON レスポンスから macro_sentiment を取得
      - API 呼び出しでのリトライ・5xx 判定・JSON パース失敗時のフォールバック（macro_sentiment=0.0）を実装
      - レジームスコア合成後に market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
      - エラー時はロールバックし上位に例外を伝播

  - データ基盤 (kabusys.data)
    - calendar_management:
      - market_calendar テーブルを利用した営業日判定・導出ユーティリティを実装
        - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供
      - DB に登録がない日については曜日ベース（土日）でフォールバック
      - 次/前営業日の探索は最大探索日数制限（_MAX_SEARCH_DAYS）を設け無限ループを防止
      - calendar_update_job を実装:
        - J-Quants API からカレンダー差分をフェッチし market_calendar を冪等更新
        - バックフィル（直近 _BACKFILL_DAYS 日間は常に再フェッチ）と健全性チェック（将来日付の異常検知）
        - 取得・保存の成否でログ出力し、失敗時は 0 を返す
      - jquants_client 経由でデータ取得/保存を呼び出す設計

    - pipeline / etl:
      - ETLResult データクラスを公開（kabusys.data.pipeline.ETLResult を kabusys.data.etl から再エクスポート）
      - ETLResult は取得数・保存数・品質問題・エラー概要などを保持し to_dict によりシリアライズ可能
      - pipeline モジュールは差分更新・保存（冪等）・品質チェックの処理方針を文書化
      - ETL 実装の設計方針:
        - 差分更新デフォルトは営業日1日分
        - backfill により最終取得日からの再取得で API 後出し修正を吸収
        - 品質チェックは致命的エラーがあっても処理を継続し、呼び出し元で評価可能にする（Fail-Fast ではない）
        - id_token 等の依存注入でテスト容易性を確保
      - DuckDB との互換性考慮（DuckDB 0.10 における executemany の空リスト制約等）を反映した実装

  - 研究用 / ファクター計算 (kabusys.research)
    - factor_research:
      - モメンタム（1M/3M/6M）、200日 MA 乖離、ATR（20日）、平均売買代金、出来高比率等を DuckDB + SQL で計算
      - データ不足時の None 扱い（安全な計算）
      - 各関数は prices_daily / raw_financials のみ参照し外部 API へはアクセスしない
      - 結果は (date, code) を含む dict のリストで返却
    - feature_exploration:
      - 将来リターン計算 (calc_forward_returns): 複数ホライズンに対応、horizons の検証（正の整数かつ <=252）
      - IC（Information Coefficient）計算（スピアマンランク相関）を実装
      - rank 関数: 同順位は平均ランクで処理（丸めで ties 検出の安定化）
      - factor_summary: count/mean/std/min/max/median を算出（None 値除外）
      - 実装は外部ライブラリに依存せず標準ライブラリのみを使用

品質・設計上の注記
  - ルックアヘッドバイアス対策:
    - AI・研究モジュールは内部で datetime.today() / date.today() を参照せず、明示的な target_date を要求
    - DB クエリは target_date 未満または target_date を境にルックアヘッドを避ける設計
  - フェイルセーフ設計:
    - 外部 API（OpenAI / J-Quants）失敗時は可能な限りフォールバック（0.0 など）またはチャンクスキップによって処理継続
  - テスト容易性:
    - OpenAI 呼び出し部分はプライベート関数を patch して置換可能
  - DuckDB 互換性考慮:
    - executemany に空リストを投げない等、実運用での互換性に配慮した実装

既知の制約 / 未実装事項
  - strategy / execution / monitoring などの一部公開 API 名は __all__ に含まれるが、このリリースにおいては該当モジュールの実装が含まれていない（将来追加予定）
  - 一部メトリクス（PBR・配当利回り等）は現フェーズで未実装（calc_value にて注記）
  - OpenAI モデルの選定やパラメータは現時点の暫定値（gpt-4o-mini 等）

セキュリティ
  - 特記事項なし（このリリースでは機密情報の取り扱いは環境変数経由を推奨）

注: 本 CHANGELOG はソースコードから推測して作成したものであり、将来的な変更や補足はプロジェクトの実装状況に応じて更新してください。