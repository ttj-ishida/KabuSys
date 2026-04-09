CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
各リリースは SemVer に従います。

[Unreleased]
-------------

- なし

[0.1.0] - 2026-04-09
--------------------

Added
- 基本パッケージ初期実装を追加（kabusys v0.1.0）。
  - パッケージエントリポイント: src/kabusys/__init__.py にて __version__ = "0.1.0" を公開。
  - サブパッケージ公開: data, strategy, execution, monitoring を __all__ で公開。

- 環境設定・自動 .env ロード機能（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探す）から自動読み込み。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
  - .env パーサ実装: export KEY=val 形式、シングル/ダブルクォート内のエスケープ、インラインコメントの扱いなどに対応。
  - Settings クラスを提供し、J-Quants / kabu / LINE / DB パス / PaperTrading 設定 / 監視閾値 / ログレベル等の取得 API を公開。
  - 必須環境変数未設定時は _require() が ValueError を投げる仕様。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores テーブルへ保存する機能を実装（score_news）。
  - バッチ処理: 最大 20 銘柄 / API コール、1銘柄あたり最大記事数・文字数でトリム。
  - OpenAI 呼び出しは JSON Mode を使い、厳密な JSON レスポンスを期待。レスポンスパースの復元ロジック（前後余剰テキストから {} を抽出）を実装。
  - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装。その他のエラーはスキップして継続（フェイルセーフ）。
  - スコアのバリデーションと ±1.0 クリップ、部分失敗時に既存のスコアを保護するための差分 DELETE → INSERT ロジックを採用（DuckDB の executemany 空リスト制約への対応あり）。
  - calc_news_window ユーティリティを提供（JST ベースのニュース集計ウィンドウを UTC naive datetime で返却）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定し market_regime テーブルへ書き込む機能を実装（score_regime）。
  - OpenAI 呼び出しのリトライ/バックオフ、API 失敗時のフォールバック（macro_sentiment=0.0）、および DB 操作での冪等（BEGIN / DELETE / INSERT / COMMIT）を実装。
  - ルックアヘッドバイアス回避設計: target_date 未満のデータのみ参照、datetime.today() / date.today() を直接参照しない。

- 研究/ファクター計算（kabusys.research）
  - ファクター計算モジュールを追加:
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離を計算。
    - calc_volatility: 20 日 ATR / 相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算。
  - 特徴量探索モジュールを追加:
    - calc_forward_returns: 指定ホライズンの将来リターンを一括で取得（柔軟な horizons 引数、最大 252 日制約、SQL によるリード計算）。
    - calc_ic: スピアマンランク相関（IC）をランクに基づいて計算。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランク扱いのランク関数（丸めによる ties 検出の対策あり）。
  - 設計方針として DuckDB 接続を受け取り prices_daily / raw_financials のみ参照、本番 API にアクセスしないよう分離。

- データ基盤ユーティリティ（kabusys.data）
  - ETL 関連:
    - ETLResult データクラス（pipeline.ETLResult を re-export）を実装し、取得件数・保存件数・品質問題・エラー一覧を集約。
    - pipeline モジュール: 差分更新、バックフィル、品質チェックの結果集約などの設計を反映。
  - カレンダー管理:
    - market_calendar の夜間バッチ更新 job (calendar_update_job) を実装。J-Quants から差分取得→save（冪等保存）を行う。
    - 営業日判定 API: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB 登録値優先、未登録日は曜日ベースでフォールバック。最大探索範囲制限、健全性チェック、バックフィルを実装。

Changed
- ロバストネスと安全性を重視した設計を各所で採用。
  - DuckDB の executemany の空リスト制約に対応する安全な削除/挿入ロジックを採用（部分失敗時の既存データ保護）。
  - OpenAI 呼び出しは専用の内部関数で抽象化し、unittest.mock.patch で差し替え可能にしてテスト容易性を向上。
  - API レスポンスのパース失敗や 5xx 系エラーに関して詳細なログ出力とフォールバックを追加。

Fixed
- DB トランザクション失敗時のハンドリングを強化（例外発生時に ROLLBACK 試行、ROLLBACK の失敗は警告ログとして記録）。

Security
- 環境変数読み込みにおいて OS 環境変数を protected として .env により上書きされないよう保護（_load_env_file の protected 引数）。これにより意図しない環境値上書きを防止。

Notes / Design decisions
- ルックアヘッドバイアス防止:
  - AI 評価・ファクター計算・ニュース集約の全処理で、target_date 未満・明確な時間ウィンドウのみを参照する実装方針を採用。
- フェイルセーフ設計:
  - 外部 API（OpenAI / J-Quants）の障害が発生しても処理を継続またはフォールバックして安全に終了するよう設計（例: macro_sentiment=0.0、該当チャンクのみスキップ）。
- DuckDB 互換性考慮:
  - SQL 実装で ROW_NUMBER / window 関数を利用しつつ、executemany の制約など実運用で遭遇する制限に対応。

Breaking Changes
- なし（初回リリース）。

開発者向けメモ
- テストしやすさを考慮して OpenAI 呼び出し箇所は _call_openai_api を patch して差し替え可能。  
- .env パーサの挙動（クォート・コメントの扱い）は細かく調整しているため、.env.example を参照して適切に設定してください。