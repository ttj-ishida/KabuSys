# Changelog

すべての重要な変更履歴を記録します。本ファイルは Keep a Changelog の形式に準拠しています。

## [Unreleased]

なし

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買 / データ基盤 / リサーチ用ユーティリティ群を実装しました。主な追加点は以下の通りです。

### 追加 (Added)

- パッケージ基礎
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ として公開。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート検出は __file__ を起点に親ディレクトリを探索し .git または pyproject.toml を基準に判定。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーを実装（コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの取り扱いを考慮）。
  - override / protected オプションにより OS 環境変数保護や上書き制御を提供。
  - Settings クラスを実装し、以下のプロパティを提供:
    - jquants_refresh_token, kabu_api_password, kabu_api_base_url
    - slack_bot_token, slack_channel_id
    - duckdb_path, sqlite_path
    - env（development / paper_trading / live の検証）、log_level（DEBUG/INFO/... の検証）
    - is_live / is_paper / is_dev の簡易判定

- AI（自然言語処理）モジュール
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）にバッチ送信してセンチメントを算出。
    - バッチ処理（最大 20 銘柄／回）、1 銘柄あたり記事数上限・文字数上限によるトリムを実装。
    - リトライ（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）、レスポンス検証、スコア ±1 クリップ、部分成功時の DB 書き換え保護（該当コードのみ DELETE → INSERT）を実装。
    - OpenAI 呼び出しを _call_openai_api として抜き出し、テストで差し替え可能に（unittest.mock.patch 用）。
    - calc_news_window 関数を提供（前日 15:00 JST ～ 当日 08:30 JST 相当の UTC 範囲を返す）。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF (1321) の 200 日移動平均乖離（重み 70%）とニュースベースのマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を参照して ma200_ratio を算出、マクロニュースを抽出し OpenAI でセンチメントを評価。
    - API キー注入可、API 失敗時は macro_sentiment=0.0 のフェイルセーフ、OpenAI 呼び出しのリトライ・エラーハンドリングを実装。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理を実装。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。

- リサーチ / ファクター計算 (src/kabusys/research)
  - factor_research.py
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER、ROE）などの定量ファクター計算関数を実装:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
    - DuckDB 上の SQL とウィンドウ関数で実装。データ不足時は None を返す設計。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、ランク変換（rank）、ファクター統計サマリ（factor_summary）を実装。
    - calc_ic は Spearman の ρ（ランク相関）を計算。
  - research パッケージの __init__ で主要関数を再エクスポート（zscore_normalize は data.stats から）。

- データ基盤ユーティリティ (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day 等の営業日判定 API を実装。
    - market_calendar テーブルがない場合は曜日ベース（土日休）でフォールバックする一貫した挙動を提供。
    - カレンダー更新ジョブ (calendar_update_job) を実装し、J-Quants から差分取得→保存（バックフィル・健全性チェックあり）を行う。
    - 最大探索日数制限や NULL 値の扱いなどの堅牢化を実装。
  - ETL パイプライン (src/kabusys/data/pipeline.py)
    - ETLResult データクラスを追加（ETL 実行のメタ情報、品質問題、エラーリストを管理）。
    - テーブル存在確認や最大日付取得等のユーティリティを実装。
    - 差分取得・バックフィル・品質チェック・idempotent 保存（jquants_client 経由）を想定した設計。
  - etl モジュール（src/kabusys/data/etl.py）で ETLResult を再エクスポート。

- DuckDB を主要なローカル解析 DB として利用する実装全般。
  - DuckDB のバージョン差異（executemany の空リスト不可など）を考慮した実装を含む。

### 変更 (Changed)

- （初回リリースのため該当なし）

### 修正 (Fixed)

- （初回リリースのため該当なし）

### 潜在的な注意事項 / 設計上の決定

- ルックアヘッドバイアス回避: news / regime / factor の各モジュールは datetime.today()/date.today() に依存せず、必ず外部から target_date を受け取る設計。
- フェイルセーフ: OpenAI API の失敗やレスポンスパース失敗時は例外を投げずデフォルト値で継続する箇所がある（ニュース・レジーム評価等）。ただし DB 書き込み失敗は上位へ伝播する。
- テスト容易性: OpenAI 呼び出しは内部関数に抽出されており、テスト時にモック差し替えが可能。
- JSON レスポンス処理は堅牢化（JSON mode でも前後余計なテキストが混ざるケースを考慮して中括弧で抽出）。
- DB トランザクションは明示的に BEGIN / COMMIT / ROLLBACK を使用し、ROLLBACK 失敗時は警告ログを出力する実装。

### 既知の制限 / 未実装

- Strategy / execution / monitoring の具体的な売買・発注ロジックはこのリリースでは含まれておらず、それらのパッケージプレースホルダが存在します。
- PBR・配当利回り等のバリューファクターは現バージョンでは未実装（calc_value に注記あり）。
- いくつかの外部クライアント（jquants_client 等）は参照されているが、この差分からは具体的な実装は推測の範囲です。

---

この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノート作成時は、コミット履歴やリリース担当者の意図に基づいて調整してください。