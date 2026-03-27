# Changelog

すべての重要な変更をここに記録します。本ファイルは「Keep a Changelog」形式に準拠しています。  
初期リリース（v0.1.0）はパッケージの主要機能群（データ ETL / カレンダー管理 / リサーチ用ファクター計算 / ニュース NLU / 市場レジーム判定 等）を実装しています。

## [0.1.0] - 2026-03-27

### 追加
- パッケージ初期リリース。モジュール構成（主要な公開 API）を追加。
  - kabusys パッケージメタ情報
    - __version__ = 0.1.0、__all__ に data, strategy, execution, monitoring を定義（strategy 等は将来の実装対象）。
- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数を読み込む自動ローダを実装。
    - 自動ロードの探索はパッケージファイル位置を基点にプロジェクトルート（.git または pyproject.toml）を検出するため、CWD に依存しない。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env のパース実装（コメント・export プレフィックス・シングル/ダブルクォート・バックスラッシュエスケープに対応）。
  - 保護された OS 環境変数（既存の os.environ）を上書きしない仕組みを導入（override / protected）。
  - Settings クラスを提供し、アプリケーション設定をプロパティで取得可能：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト）、SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - データベースパス設定: DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）
    - 環境種別検証（KABUSYS_ENV: development / paper_trading / live）およびログレベル検証（LOG_LEVEL）
    - is_live / is_paper / is_dev の判定ユーティリティ

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出し ai_scores テーブルへ保存する処理を実装。
  - 主な機能/設計:
    - ニュース収集ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）
    - 1 銘柄あたり最大記事数・最大文字数でトリム（トークン肥大化対策）
    - 最大 20 銘柄/バッチで API 呼び出し（_BATCH_SIZE）
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフとリトライ
    - JSON Mode を使ったレスポンスバリデーション（結果形式検査・スコア数値化・±1.0 クリップ）
    - 部分失敗対策として、取得済み銘柄のみ DELETE → INSERT で置換（既存スコア保護）
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（モジュール内 _call_openai_api）

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定し market_regime テーブルへ冪等書き込みする機能を追加。
  - 主な実装ポイント:
    - 1321 の直近 200 日データを用いた ma200_ratio 計算（target_date 未満のデータのみを利用しルックアヘッドを防止）
    - マクロキーワードに基づく raw_news タイトル抽出（最大 20 件）
    - OpenAI（gpt-4o-mini）でのマクロセンチメント評価（JSON 出力期待）
    - API エラー時のフェイルセーフ（macro_sentiment = 0.0）とリトライ
    - スコア合成式: clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)
    - 閾値によりラベル化し、market_regime テーブルへ BEGIN / DELETE / INSERT / COMMIT の冪等操作で保存
    - OpenAI API キー未設定時は ValueError を返すチェック

- リサーチ用ファクター計算（kabusys.research）
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離率（データ不足時は None）
    - calc_volatility: 20 日 ATR（avg true range）、相対 ATR、20 日平均売買代金、出来高比率
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算（EPS 欠損や 0 の場合は None）
    - 計算は DuckDB の prices_daily / raw_financials を参照。外部 API にはアクセスしない。
  - feature_exploration モジュール:
    - calc_forward_returns: 将来リターン（指定ホライズン）を一括 SQL で取得（デフォルト horizons=[1,5,21]）
    - calc_ic: スピアマンのランク相関（IC）計算。3 銘柄未満で計算不可（None を返す）
    - rank: 同順位は平均ランクで扱う安定したランク関数（丸め処理で ties 検出を安定化）
    - factor_summary: count/mean/std/min/max/median の統計サマリーを純粋 Python 実装で提供

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - market_calendar を利用した営業日判定ユーティリティを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にカレンダーが無い場合は曜日ベースのフォールバック（平日が営業日）を提供
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新（バックフィル・健全性チェックを実装）
    - 最大探索範囲制限（_MAX_SEARCH_DAYS）等、安全対策を実装
  - ETL パイプライン（kabusys.data.pipeline）:
    - ETLResult データクラスを実装（取得件数・保存件数・品質問題・エラー一覧を格納）
    - 差分取得、バックフィル、品質チェック（quality モジュールとの組合せ）を想定した設計（実際の jquants_client 呼び出しを使用）
  - etl モジュールは pipeline.ETLResult を再エクスポート

### 変更
- 設計方針や実装ポリシーをコード内ドキュメントとして明確化:
  - ルックアヘッドバイアス防止のため、ニュース/NLP/レジーム判定/ファクター計算等では datetime.today()/date.today() を参照しない実装方針（外部から target_date を注入する設計）。
  - DuckDB の executemany に関する互換性問題に対する回避（空リストの扱いを明示）。

### 修正（設計上のフォールバック / フェイルセーフ）
- OpenAI / J-Quants 等の外部 API 呼び出しに対して堅牢なエラー処理を追加:
  - レート制限・ネットワークエラー・タイムアウト・5xx に対するリトライとバックオフ。
  - それ以外のエラーやレスポンスパース失敗時は処理をスキップして継続（例外を大域で落とさないフェイルセーフ）。
- DB 書き込みは冪等操作（DELETE → INSERT、BEGIN/COMMIT/ROLLBACK 管理）で安全に行う実装。

### セキュリティ / バリデーション
- 必須環境変数未設定時に明示的な ValueError を返す（OpenAI キーや Slack トークン等）。
- KABUSYS_ENV / LOG_LEVEL の値検証を実装し、不正値はエラーとする。

### 既知の制限・今後の作業予定
- パッケージルートの __all__ に strategy / execution / monitoring が含まれるが、今回のリリースにそれらのモジュールの実装は含まれていません（将来的な実装予定）。
- 現在の AI 部分は OpenAI の JSON Mode に依存するため、API の仕様変更や SDK のバージョン差異に注意が必要。
- 一部の DB バインドや DuckDB の挙動はバージョン依存性があるため、運用時に互換性確認が推奨されます。

### 破壊的変更
- なし（初回リリース）

--- 

今後のリリースでは、戦略実行（strategy / execution）・モニタリング（monitoring）の実装、テストカバレッジの強化、運用上の監視/アラート機能の追加を予定しています。