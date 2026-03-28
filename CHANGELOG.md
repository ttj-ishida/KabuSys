# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  
現在のバージョンは 0.1.0 です。

※日付はリリース日を表します。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買プラットフォームのコア機能群を実装・公開しました。

### Added
- パッケージ構成
  - パッケージのエントリポイントを実装（kabusys.__init__）。
  - モジュール階層: data, research, ai, config, 等を提供。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動ロードする仕組みを実装。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を探索して自動ロード）。
  - .env/.env.local の読み込み順序と上書きルール（OS 環境変数保護）を実装。
  - .env 行のパーシングが強化（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス等の設定プロパティを公開。
  - env/log_level のバリデーション（許容値チェック）と利便性プロパティ（is_live / is_paper / is_dev）。

- AI 関連（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）で銘柄別センチメントを JSON Mode で取得する機能（score_news）。
    - チャンク処理（最大 20 銘柄/1 コール）、記事および文字数トリム、バッチリトライ（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）を実装。
    - レスポンスの厳格なバリデーション処理およびスコアの ±1.0 クリッピングを実装。
    - DuckDB への冪等書き込み（該当コードのみ DELETE → INSERT）を実装。
    - テスト容易性のため _call_openai_api をパッチ差し替え可能に設計。
    - タイムウィンドウ計算ユーティリティ calc_news_window を提供（JST ベースの窓を UTC naive datetime として返す）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を評価する score_regime を実装。
    - マクロニュース抽出、OpenAI 呼び出し（gpt-4o-mini）、リトライ処理、フェイルセーフ（API 失敗時 macro_sentiment=0）を実装。
    - レジーム判定結果を market_regime テーブルへ冪等に書き込む（BEGIN / DELETE / INSERT / COMMIT）。
    - ルックアヘッドバイアスを避ける設計（内部で date.today()/datetime.today() を参照しない、DB クエリは target_date 未満のデータのみ使用）。

- Data / ETL（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar を用いた営業日判定ユーティリティを提供（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB 登録データ優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - calendar_update_job により J-Quants からカレンダーの差分取得・冪等保存を実装（バックフィル・健全性チェック含む）。

  - ETL パイプライン基盤（kabusys.data.pipeline / etl）
    - ETL 実行結果を表す ETLResult データクラスを提供（品質チェック結果やエラー集約、to_dict 等のユーティリティ）。
    - 差分更新のための内部ユーティリティ（テーブル存在チェック・最大日付取得等）を実装。
    - jquants_client と quality モジュールを利用する設計に基づく ETL ワークフローの骨子を整備。
    - etl モジュールが pipeline.ETLResult を公開再エクスポート。

- Research（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、相対 ATR、出来高指標）、Value（PER, ROE）を計算する関数を実装（calc_momentum / calc_volatility / calc_value）。
    - DuckDB を用いた SQL ベースの実装で、外部 API には依存しない設計。
    - データ不足時の None 扱い等を明確に実装。

  - 特徴量探索ユーティリティ（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic）、ランキング（rank）、統計サマリー（factor_summary）を実装。
    - Spearman（ランク）ベースの IC 計算、同順位は平均ランクで処理。
    - pandas 等に依存せず標準ライブラリ + DuckDB のみで実装。

### Changed
- 新規リリースのため該当なし。

### Fixed
- 新規リリースのため該当なし。

### Implementation / Design notes（実装上の注記）
- API 呼び出しについては堅牢性重視：
  - OpenAI 呼び出しはリトライと指数バックオフを実装し、致命的失敗時もシステム全体を停止させずフェイルセーフ値で継続する方針。
  - News NLP と Regime Detector はそれぞれ独立した _call_openai_api 実装を持ち、モジュール間でプライベート関数を共有しない設計（結合を低減）。
- DB 書き込みは冪等性を意識：
  - market_regime / ai_scores などは該当日の既存レコードを削除してから挿入する方式を採用（部分失敗時にも既存データを不必要に消さない配慮）。
  - DuckDB の executemany に関する互換性（空リスト不可）への対応を実装。
- ルックアヘッドバイアス対策：すべての分析関数は target_date を明示的に受け取り、内部で現在日時を参照しない設計。
- テスト支援：
  - OpenAI 呼び出し部分は unittest.mock.patch 等で差し替え可能に実装しているため、単体テストが容易。

### Known limitations / TODO
- 一部ファクター（PBR・配当利回り）は未実装（calc_value の注記参照）。
- jquants_client / quality モジュール依存のため、それらの実装・外部 API レスポンスに応じた追加ハンドリングが必要な場合がある。
- セキュリティ：環境変数の取り扱いは基本的な保護を行っているが、実運用前にシークレット管理（Vault 等）導入検討推奨。

---

（参考）完全な変更履歴はリポジトリのコミットログを参照してください。