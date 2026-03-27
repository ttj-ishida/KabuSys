# Changelog

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」仕様に準拠しています。  
バージョン番号は semantic versioning に従います。

## [Unreleased]
- （現時点の変更はすべて v0.1.0 として初期リリースに含まれています）

## [0.1.0] - 2026-03-27

初期リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。主な追加点は以下の通りです。

### Added
- パッケージのエントリポイント
  - src/kabusys/__init__.py によるパッケージ初期化と __version__ = "0.1.0"、主要サブパッケージの公開 (`data`, `strategy`, `execution`, `monitoring`)。

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルートの検出は .git / pyproject.toml を基準）。
    - .env/.env.local の読み込みルール（OS 環境変数優先、.env.local は上書き）と KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
    - .env パースの堅牢化（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理など）。
    - Settings クラスによる型付きプロパティ（J-Quants / kabu / Slack / DB パス / 環境 / ログレベル等）と妥当性チェック（env, log_level の検証、必須変数チェック）。

- AI 関連（OpenAI ベースの NLP）
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols を使ったニュース集約 → 銘柄ごとにニュースを束ねて OpenAI（gpt-4o-mini）へ JSON Mode で問い合わせ、センチメントスコア（-1.0〜1.0）を ai_scores テーブルへ書き込み。
    - 時間ウィンドウ計算（前日15:00 JST〜当日08:30 JST を UTC に変換して扱う calc_news_window）。
    - バッチ処理（最大 20 銘柄 / チャンク）、記事数/文字数上限（記事数: 10 件、文字上限: 3000 文字）を導入してトークン肥大化に対処。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ、レスポンスの厳密なバリデーション（JSON 抽出、results 構造検査、コード照合、スコアの数値検証、±1.0 クリップ）。
    - テスト容易性を考慮した _call_openai_api の差し替えポイント（unittest.mock.patch 可）。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ冪等書込を行う score_regime を実装。
    - マクロニュース抽出（キーワードベース）、OpenAI 呼び出しに対する堅牢なリトライとフェイルセーフ（失敗時 macro_sentiment = 0.0）。
    - ルックアヘッドバイアス回避設計（datetime.today()/date.today() を参照しない、DB クエリでは target_date 未満のみ使用）。
    - JSON パースや API エラーに対する細かなログ出力と安全なフォールバック。

- データプラットフォーム（DuckDB を想定）
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理ロジック（market_calendar テーブル）と夜間バッチ更新ジョブ（calendar_update_job）。
    - 営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB データ優先の挙動（未登録日は曜日ベースでフォールバック）、探索上限 (_MAX_SEARCH_DAYS) による無限ループ防止、バックフィル・健全性チェック実装。

  - src/kabusys/data/pipeline.py
    - ETL パイプラインの基盤（差分取得 → 保存 → 品質チェック）に対応するユーティリティ。
    - ETLResult dataclass による実行結果集約（取得数・保存数・品質問題・エラー一覧）、has_errors / has_quality_errors / to_dict を提供。
    - 内部ユーティリティ（テーブル存在チェック、最大日付取得、トレーディングデイ補正ロジック等）。

  - src/kabusys/data/etl.py
    - pipeline.ETLResult の公開再エクスポート。

  - src/kabusys/data/__init__.py
    - パッケージ初期化プレースホルダ（将来の公開 API の入口）。

- リサーチ（因子・特徴量探索）
  - src/kabusys/research/factor_research.py
    - ファクター計算（Momentum / Value / Volatility / Liquidity）を実装:
      - calc_momentum: 1M/3M/6M リターン、ma200_dev（200 日移動平均乖離）
      - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比
      - calc_value: PER（price / EPS）、ROE（raw_financials の最新データを使用）
    - DuckDB 上で SQL とウィンドウ関数を用いた効率的な実装。データ不足時は None を返す。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns: 任意ホライズンに対応、デフォルト [1,5,21]）。
    - IC（Information Coefficient）計算（calc_ic: Spearman ランク相関）、ランク関数（rank）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）。
    - 外部ライブラリに依存せず標準ライブラリ / DuckDB のみで実装。

- テスト・運用を意識した設計
  - OpenAI 呼び出し部分はモジュール単位で差し替え可能な設計（テストのモック化を想定）。
  - DB 書き込みはトランザクションで冪等性を確保（BEGIN / DELETE / INSERT / COMMIT、失敗時 ROLLBACK の試行）。
  - API キー未設定時に ValueError を投げる明示的なエラーメッセージ（OPENAI_API_KEY、SLACK_BOT_TOKEN 等）。

### Changed
- （新規リリースのため該当なし）

### Fixed
- （新規リリースのため該当なし）

### Deprecated
- なし

### Removed
- なし

### Security
- 外部 API キーは環境変数または明示的引数で注入する設計。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。

Notes / 設計上の留意点
- すべての処理は「ルックアヘッドバイアス」を避ける設計になっており、内部で現在時刻を参照せず、target_date を明示的に受け取る API を採用しています。
- OpenAI は gpt-4o-mini を想定（JSON Mode を利用）。API エラーや不正レスポンスに対してはフェイルセーフ（スコア 0.0、または該当銘柄スキップ）で動作します。
- DuckDB のバージョン依存性（executemany の空リスト不可等）を考慮した実装上の注意があります。

貢献・バグ報告
- 不具合や改善提案があれば issue を立ててください。README / CONTRIBUTING は将来追加予定です。