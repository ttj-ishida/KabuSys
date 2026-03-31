# Changelog

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」方式に準拠します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-31

初回リリース

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化。バージョン: 0.1.0。公開サブパッケージ候補: data, strategy, execution, monitoring。
- 設定・環境変数管理 (kabusys.config)
  - Settings クラスを導入し、環境変数から各種設定（J-Quants / kabuステーション API / Slack / DBパス / 実行環境フラグ等）を取得する API を提供。
  - 環境値検証（KABUSYS_ENV の有効値チェック、LOG_LEVEL の有効値チェック）を実装。
  - .env 自動ロード機能を実装（読み込み優先順位: OS環境変数 > .env.local > .env）。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` によって無効化可能。
  - .env ファイルパーサを実装し、`export KEY=val` 形式、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱いに対応。
  - OS側の既存環境変数を保護する仕組み（protected set）を導入し、`.env.local` の上書き時にも保護可能。
  - 必須環境変数取得時は未設定だと ValueError を送出するユーティリティ `_require` を提供。
- データ（DuckDB）連携・ETL 基盤 (kabusys.data)
  - ETL の公開インターフェース ETLResult を提供（kabusys.data.pipeline を再エクスポート）。
  - ETL パイプライン（kabusys.data.pipeline）を実装:
    - 差分取得、バックフィル、品質チェックのための基本構造を提供。
    - ETLResult データクラス（取得件数、保存件数、品質問題・エラー情報、has_errors/has_quality_errors 等）を導入。
    - DuckDB テーブル存在確認や最大日付取得等のユーティリティを実装。
  - マーケットカレンダー管理（kabusys.data.calendar_management）を実装:
    - market_calendar に基づいた営業日判定 API を提供（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - カレンダーデータ未取得時は曜日ベース（平日を営業日）でフォールバックするロジックを明確化。
    - calendar_update_job により J-Quants API から差分取得して market_calendar を冪等的に更新する処理を実装（バックフィル・健全性チェック付き）。
- リサーチ（ファクター計算・特徴量探索） (kabusys.research)
  - ファクター計算モジュール（kabusys.research.factor_research）を追加:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務を取り出して PER/ROE を計算。
    - 各関数は DuckDB の prices_daily / raw_financials のみ参照し、本番発注 API などにはアクセスしない設計。
  - 特徴量探索モジュール（kabusys.research.feature_exploration）を追加:
    - calc_forward_returns: 与えられたホライズン群に対する将来リターンを計算（デフォルト: [1,5,21]）。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算。サンプル数不足時は None を返す。
    - rank, factor_summary: ランク化ユーティリティおよび基本統計量（count/mean/std/min/max/median）を提供。
  - zscore 正規化ユーティリティを kabusys.data.stats から再エクスポート（kabusys.research.__init__）。
- AI（自然言語処理）機能 (kabusys.ai)
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）を追加:
    - raw_news / news_symbols を集約し、銘柄ごとに記事をまとめて OpenAI の gpt-4o-mini（JSON Mode）へバッチ送信。
    - チャンク処理（最大20銘柄/コール）、1銘柄あたり最大記事数・最大文字数のトリム、429/ネットワーク/5xx に対する指数バックオフでのリトライ実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列、code と score の検証、数値クリップ）を実装し、ai_scores テーブルへ冪等書き込み（DELETE → INSERT）。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC で扱う calc_news_window）を提供。
    - API 呼び出し部分は _call_openai_api でラップし、テスト時に差し替え可能（unittest.mock.patch を想定）。
    - API 失敗やパース失敗は例外で停止させずフェイルセーフでスキップまたは 0.0 相当の扱い。
  - 市場レジーム判定（kabusys.ai.regime_detector）を追加:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し日次市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出（キーワードベース）、OpenAI 呼び出し（gpt-4o-mini）、リトライ/バックオフ、API 失敗時フォールバック（macro_sentiment = 0.0）等を実装。
    - ルックアヘッドバイアス防止（date.today() を用いない、prices_daily は target_date 未満のみを参照）を設計思想として明示。
- 実装上の共通設計・品質考慮
  - DuckDB を主要な分析 DB として採用。多くの集計/ウィンドウ処理は SQL（DuckDB）ベースで実装。
  - ルックアヘッドバイアス回避のため、日付参照はすべて外部から渡す target_date ベースで実装（内部で今日の日付を参照しない）。
  - OpenAI 呼び出し周りでの堅牢性（リトライ、5xx の扱い、レスポンスパース耐性）を重視。
  - テストフレンドリーな設計（外部 API 呼び出し箇所を関数でラップし差し替え可能）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 廃止 (Deprecated)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- （現時点で公開セキュリティアラートは無し）

### 既知の注意点 / マイグレーションノート
- OpenAI API キーは api_key 引数で注入可能（テスト容易性）だが、デフォルトでは環境変数 OPENAI_API_KEY を参照する。未設定時は ValueError を送出する点に注意。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）から行われる。パッケージ配布後や特異な配置では自動検出に失敗する可能性があるため、問題がある場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して手動で環境変数を用意してください。
- DuckDB の executemany は空リストを受け付けないバージョンの互換性を考慮しているため、空パラメータ配列は事前にチェックしている。
- calendar_update_job は外部 J-Quants クライアント（kabusys.data.jquants_client）を呼び出すが、当該クライアントが例外を投げた場合は job が安全に 0 を返して終了する設計。

---

今後のリリースでは、strategy/execution/monitoring 等の実稼働機能・運用用ツール、テストカバレッジ拡充、性能最適化、外部クライアントの抽象化（モック容易性向上）などを予定しています。