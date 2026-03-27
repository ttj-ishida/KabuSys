# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

※日付はリリース日を示します。

## [0.1.0] - 2026-03-27

初回リリース。日本株自動売買システムのコアモジュール群を実装しました。主な追加点と設計上の要点は以下の通りです。

### 追加 (Added)
- パッケージの基本情報
  - パッケージ名: kabusys、バージョン 0.1.0（src/kabusys/__init__.py）

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定値を読み込む自動ローダを実装。
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行い、CWDに依存しない実装。
  - .env と .env.local の読み込み優先順位（OS 環境変数 > .env.local > .env）。.env.local は .env を上書きする。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env のパースは export 形式、クォート、バックスラッシュエスケープ、行末コメントなど多様なケースに対応。
  - 必須設定取得用のヘルパー _require と Settings クラスを提供。
  - Settings が提供する主要プロパティ例:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/... の検証）
    - is_live / is_paper / is_dev ヘルパー

- AI（NLP）モジュール (src/kabusys/ai/)
  - ニュースセンチメント（銘柄単位）スコアリング: score_news（news_nlp.py）
    - gpt-4o-mini を用いた JSON モードの LLM 呼び出し。
    - 前日 15:00 JST ～ 当日 08:30 JST のウィンドウ計算（calc_news_window）。
    - 銘柄ごとに記事を集約し、最大記事数・文字数でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - バッチ処理（1 API コールあたり最大 20 銘柄）および指数バックオフによるリトライ（429/ネットワーク/5xx）。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code と score の確認）。スコアは ±1.0 にクリップ。
    - 成功した銘柄のみ ai_scores テーブルに対して DELETE → INSERT の冪等更新。
    - API キーは引数で注入可能（テスト容易性）。未設定時は OPENAI_API_KEY を参照してエラーを送出。

  - 市場レジーム判定: score_regime（regime_detector.py）
    - ETF 1321（日経225連動）の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成。
    - ma200_ratio の計算は target_date 未満のデータのみ利用し、ルックアヘッドバイアスを防止。
    - マクロニュース抽出はマクロキーワードに基づいて raw_news からタイトルを取得し、最大 20 件を LLM へ送信。
    - LLM 呼び出しは冪等的にリトライ処理を実装、API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - 合成スコアを基に regime_label を bull / neutral / bear に分類。
    - market_regime テーブルへは BEGIN/DELETE/INSERT/COMMIT の手順で冪等書き込みを行う。
    - OpenAI クライアントは引数でのキー注入か環境変数 OPENAI_API_KEY を利用。

- データ関連モジュール (src/kabusys/data/)
  - ETL パイプラインインターフェースの公開（ETLResult の再エクスポート; pipeline.py / etl.py）。
  - ETLResult（dataclass）を導入（取得件数、保存件数、品質問題、エラー一覧などを集約、to_dict を提供）。
  - pipeline.py: 差分更新・バックフィル方針・品質チェックの設計を反映したユーティリティを実装（最小日付、backfill, calendar lookahead 等）。
  - カレンダー管理（calendar_management.py）
    - JPX カレンダー（market_calendar）を用いた営業日判定 API を提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にデータがない場合は曜日ベースのフォールバック（休日は土日）を採用。
    - calendar_update_job: J‑Quants からの差分取得・バックフィル・保存処理を実装。保存は jq.fetch_market_calendar / jq.save_market_calendar を利用。

- リサーチ / ファクター分析モジュール (src/kabusys/research/)
  - factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR / atr_pct、20 日平均売買代金、出来高比率を計算。データ不足時は None を扱う。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を計算。EPS が 0/欠損時は None。
    - DuckDB を用いたウィンドウ関数・集計ベースの実装。
  - feature_exploration.py:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）での将来リターンを計算（LEAD を使用）。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算。サンプル数が少ない場合は None。
    - rank: 同順位は平均ランクを返すランク関数（丸めによる ties 対応）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。

- その他
  - モジュール間の公開制御（__all__）を整備（research/__init__.py, ai/__init__.py 等）。
  - OpenAI 呼び出しは各モジュールで個別実装（モジュール結合を避ける設計、テスト用にモック差替えが可能）。
  - DuckDB を主要なローカル分析 DB として想定。

### 変更 (Changed)
- （初回リリースにつき変更履歴はありません）

### 修正 (Fixed)
- （初回リリースにつき修正履歴はありません）

### 既知の注意点 / 設計上の決定
- ルックアヘッドバイアス除去:
  - 多くの処理（news/ai/regime/factors/forward returns）は内部で date を引数として受け取り、datetime.today()/date.today() を直接参照しない設計です。テストや運用で再現可能な計算を意図しています。
- フェイルセーフ:
  - LLM 呼び出し失敗時はスコアを 0.0 にフォールバックし、処理を継続する実装方針です（例: regime_detector の macro_sentiment、news_nlp のチャンク失敗はスキップ）。
- API キー注入:
  - OpenAI API キーは関数引数で注入可能で、未指定時は環境変数 OPENAI_API_KEY を参照します。テストでは patch により _call_openai_api を差し替え可能です。
- DB 書き込みの冪等性:
  - ai_scores / market_regime 等への書き込みは既存行を削除してから挿入することで冪等性を確保（部分失敗時に既存データを保護するため、書き込み対象コードを限定）。
- .env パーサは多くの実用ケース（クォートやエスケープ、コメント）に対応するための実装を含みますが、極端なフォーマットは未対応の可能性があります。
- DuckDB の executemany に空リストを渡せないバージョン対策など、現時点での互換性ワークアラウンドを含みます（コメント参照）。

### 将来の改善候補（メモ）
- news_nlp / regime_detector の LLM プロンプトや使用モデルは外部設定化して柔軟にできると便利。
- ETL / pipeline の監査ログ出力・メトリクス収集の強化。
- J-Quants / kabu API クライアントのモック実装やテストヘルパーの追加。

---

以上。詳細な関数一覧や使用方法は各モジュールの docstring を参照してください。