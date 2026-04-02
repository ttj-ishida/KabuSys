# Changelog

すべての重要な変更を本ファイルに記載します。本ファイルは Keep a Changelog の形式に従います。

なお、本リリース情報はリポジトリ内のソースコードから推測して記載しています。

## [0.1.0] - 2026-04-02

初回公開リリース。日本株自動売買プラットフォーム「KabuSys」のコア機能群を実装しました。主な追加点・設計方針は以下の通りです。

### 追加 (Added)
- パッケージ構成
  - kabusys パッケージを初期公開（__version__ = 0.1.0）。パブリックサブパッケージとして data, research, ai, monitoring, strategy, execution 等を想定したエクスポートを用意。
- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local ファイルまたは環境変数から設定値を読み込む自動ロード機能を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）を実装し、CWD に依存しない自動ロードを実現。
  - .env パーサーの強化：export プレフィックス対応、シングル/ダブルクォート内のエスケープ対応、インラインコメントの扱い制御などを実装。
  - 環境変数の上書き制御（override, protected）をサポートし、OS 環境変数の保護を可能に。
  - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス / 監視しきい値 / システム環境（KABUSYS_ENV, LOG_LEVEL）の検証付きプロパティを公開。
- AI モジュール (src/kabusys/ai/)
  - news_nlp.score_news: raw_news + news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信して銘柄別センチメント（ai_scores テーブル）を算出・保存する機能を実装。
    - チャンク処理（1リクエストあたり最大 20 銘柄）、1銘柄当たりの記事数/文字数制限、JSON レスポンスのバリデーション、スコア ±1.0 のクリップを実装。
    - 429（レート制限）・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装。失敗時は該当チャンクをスキップして継続するフェイルセーフ設計。
    - テスト容易性のため _call_openai_api をパッチ差し替え可能に実装。
  - regime_detector.score_regime: ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出し、market_regime テーブルへ冪等書き込みする機能を実装。
    - prices_daily からの過去データ参照は target_date 未満の排他条件でルックアヘッドを回避。
    - マクロ記事が存在する場合のみ OpenAI を呼び出し、API 失敗時は macro_sentiment=0.0 へフォールバック。
    - OpenAI 呼び出しは独立実装（news_nlp と共有しない）でモジュール結合を低減。
- Research モジュール (src/kabusys/research/)
  - factor_research: calc_momentum, calc_volatility, calc_value を実装。
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（データ不足時は None を返す）。
    - Volatility: 20 日 ATR, ATR 比率, 20 日平均売買代金、出来高比率を計算。
    - Value: raw_financials から最新財務データを取得し PER / ROE を計算（PBR・配当利回りは未実装）。
  - feature_exploration: calc_forward_returns（任意ホライズンで将来リターン算出）、calc_ic（Spearman ランク相関による IC 算出）、factor_summary（統計サマリー）、rank（ランク付け）を実装。
  - zscore_normalize は data.stats から再エクスポート。
  - 他モジュールは外部ライブラリ（pandas 等）に依存せず純粋な SQL/標準ライブラリで実装する方針。
- Data モジュール (src/kabusys/data/)
  - calendar_management: market_calendar を用いた営業日判定・探索ユーティリティを実装。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - DB に値がある場合はそれを優先し、未登録日は曜日ベースでフォールバックする一貫性あるロジック。
    - 夜間バッチ calendar_update_job を実装（J-Quants API から差分取得 → 保存、バックフィル、健全性チェック）。
  - pipeline, etl: ETLResult データクラスを実装し、ETL パイプラインの結果集約と品質チェック統合を想定するインターフェースを追加（ETLResult を data.etl から再エクスポート）。
  - DuckDB 互換性や executemany の注意点（空リスト処理）について考慮した実装。
- ロギング / フォールバック / テスト支援
  - 主要処理は詳細なログを出力する設計（info/debug/warning/exception）。
  - ルックアヘッドバイアス回避のため、内部処理は datetime.today()/date.today() を直接参照しない方針（target_date 引数ベース）。
  - 外部 API 呼び出し部分はパッチしやすい設計（ユニットテスト容易化）。

### 変更 (Changed)
- 初版のため過去バージョンからの変更点はなし（新規実装）。

### 修正 (Fixed)
- .env パーサーの細かな実装（クォート中のバックスラッシュエスケープ、export プレフィックス、コメント切り取りの扱い）を丁寧に実装し、実運用での .env 設定の堅牢性を向上。

### 既知の制限 / 注意事項 (Notable notes / Known issues)
- src/kabusys/research/factor_research.calc_value:
  - PBR・配当利回りは現バージョンでは未実装（設計コメントあり）。
- テスト設計:
  - OpenAI 呼び出しは JSON Mode を利用する想定だが、実際の SDK / API の挙動に依存するため本番運用前に実環境での確認が必要。
- DuckDB バインドの互換性:
  - executemany に空リストを渡すと問題になる DuckDB 互換性を考慮してガードを入れています。環境により挙動差があるため注意。
- 致命的な実装問題（要修正）
  - src/kabusys/data/pipeline.py の末尾付近で関数 _get_max_date の戻り処理が途中で切れているように見える（ファイル断片に "return date.fro" のような不完全なコードが存在）。これは現状のソースコピーの断片に由来する可能性が高く、実行時に SyntaxError / NameError を引き起こします。リリース前に該当箇所の完全な実装・静的解析・ユニットテストを行う必要があります。
- 一部ファイルが省略または未実装の可能性
  - src/kabusys/data/__init__.py が空の状態（エクスポート整理が必要）等、リポジトリ全体の組立ては追加のメンテナンスが必要。

### セキュリティ (Security)
- 外部 API キーは環境変数（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）で管理する設計です。.env の自動ロード機能を採用していますが、本番では OS 環境変数による管理やシークレットストアの使用を推奨します。
- .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テストや CI 用）。

---

今後の予定（推定）
- pipeline モジュールの未完部分修正とユニットテスト整備。
- add: strategy / execution / monitoring の実装と統合テスト（実際の発注 API とは明確に分離し安全策を追加）。
- refine: AI プロンプトやレスポンス処理の堅牢化、OpenAI SDK バージョン差分への対応。
- implement: 追加のファクター（PBR、配当利回り）や Research 用ユーティリティの拡張。

もし差分の詳細（コミットログや追加ファイル）や日付の調整が必要であれば、それに合わせて CHANGELOG を更新します。