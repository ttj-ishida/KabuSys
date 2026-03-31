# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトの最初のリリースを記録しています。

## [0.1.0] - 2026-03-31

最初の公開リリース。

### Added
- 基本パッケージとバージョン情報を追加
  - パッケージ: kabusys
  - バージョン: 0.1.0
  - エクスポート: data, strategy, execution, monitoring
  - ファイル: src/kabusys/__init__.py

- 環境変数・設定管理
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）を基準に自動読み込み（無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を用意）。
  - export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、コメント処理等の堅牢なパーサ実装。
  - .env の上書き制御（override / protected）をサポートし、OS 環境変数を保護。
  - 必須環境変数チェック（_require）と明確なエラーメッセージ。
  - Settings クラスでアプリケーション設定を提供（J-Quants, kabu API, Slack, DBパス, 環境判定, ログレベルなど）。
  - ファイル: src/kabusys/config.py

- ニュース NLU（OpenAI）による銘柄別センチメントスコアリング
  - raw_news と news_symbols を用い、銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）の JSON Mode でバッチ評価。
  - バッチ処理（最大 20 銘柄）、記事トリム（最大記事数・最大文字数）、429/ネットワーク/5xx に対する指数バックオフリトライ。
  - レスポンスの厳密なバリデーション（JSON 抽出、results フォーマット、コード照合、スコア数値チェック）、スコア ±1.0 にクリップ。
  - ai_scores テーブルへの冪等的な置換（DELETE → INSERT、部分失敗時に既存データを保護）。
  - テスト容易性のため API 呼び出し関数をモジュール内でパッチ置換可能に実装。
  - 関数: score_news, calc_news_window, 他
  - ファイル: src/kabusys/ai/news_nlp.py

- マクロ＋テクニカルを組み合わせた市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
  - DuckDB からの過去データ取得は target_date 未満のみを使用し、ルックアヘッドバイアスを防止。
  - OpenAI 呼び出しは専用実装、API 失敗時は macro_sentiment=0.0 でフォールバック。
  - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）と ROLLBACK ハンドリング。
  - 関数: score_regime, _calc_ma200_ratio, _fetch_macro_news, _score_macro
  - ファイル: src/kabusys/ai/regime_detector.py

- リサーチ（ファクター計算・特徴量探索）モジュール
  - ファクター計算（Momentum / Value / Volatility / Liquidity）:
    - モメンタム: 1M/3M/6M リターン、200日 MA 乖離（データ不足時は None）。
    - ボラティリティ: 20日 ATR、相対 ATR、20日平均売買代金、当日出来高比率。
    - バリュー: PER、ROE（raw_financials から最新報告を取得）。
  - 将来リターン計算（複数ホライズン対応、ホライズンの検証）。
  - IC（Spearman のランク相関）計算：同順位の平均ランク処理、必要件数未満は None。
  - 統計サマリー（count/mean/std/min/max/median）。
  - データ依存は DuckDB の prices_daily / raw_financials のみ（本番APIや発注には非依存）。
  - ファイル: src/kabusys/research/factor_research.py, src/kabusys/research/feature_exploration.py, src/kabusys/research/__init__.py

- データ基盤（DuckDB）とカレンダー管理、ETL パイプライン
  - 市場カレンダー管理:
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar が存在しない場合は曜日ベースでフォールバック。
    - JPX カレンダーを J-Quants API から差分取得する夜間バッチ（calendar_update_job）、バックフィルと健全性チェックを実装。
    - ファイル: src/kabusys/data/calendar_management.py
  - ETL パイプライン基盤:
    - ETLResult dataclass を提供（取得数・保存数・品質問題・エラー等を記録）。
    - 差分取得のための最終日取得・テーブル存在チェックユーティリティを実装。
    - 設計: 差分更新、バックフィル、品質チェックの集約とエラー集計（Fail-Fast ではなく呼び出し元で判断）。
    - ファイル: src/kabusys/data/pipeline.py, src/kabusys/data/etl.py
  - jquants_client との連携用プレースホルダ（モジュール参照あり）。

- ユーティリティ設計上の注意点（横断的な設計方針）
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() を直接参照しない設計（target_date を明示的に渡す）。
  - DuckDB のバージョン差異（executemany の空リスト制約など）に配慮した実装。
  - ロギングと細かな警告メッセージを充実（データ欠損、API エラー、ROLLBACK 失敗等）。
  - テスト容易性のため API 呼び出し箇所へ差し替え（patch）を想定した関数境界を用意。

### Changed
- 初回リリースにつき該当なし

### Fixed
- 初回リリースにつき該当なし

### Deprecated
- 初回リリースにつき該当なし

### Removed
- 初回リリースにつき該当なし

### Security
- 初版では機密情報の取り扱いに関する注意点を設定モジュールで明示（必須トークンは環境変数で、.env.example を参照する旨を案内）。

注記:
- 本リリースはコードベースから推測した機能一覧です。実装の正確な挙動や API キーの扱い、外部依存（OpenAI, J-Quants 等）の詳細は実行環境・設定に依存します。必要に応じて各モジュールの README やドキュメントを参照してください。