# Changelog

すべての重要な変更はこのファイルに記録します。本ファイルは「Keep a Changelog」仕様に準拠します。  
日付はコミット時点（本推定では 2026-03-31）を使用しています。内容は提供されたコードベースから推測して記載しています。

## [Unreleased]
- (なし)

## [0.1.0] - 2026-03-31
初回リリース（推定）。以下の主要機能と設計方針を実装しています。

### 追加
- パッケージ基盤
  - パッケージメタ情報 __version__ = "0.1.0" を追加。
  - パブリック API 用にモジュール群を __all__ でエクスポート（data, strategy, execution, monitoring 等を想定）。

- 設定管理（kabusys.config）
  - .env ファイルまたは環境変数からの設定読み込みを自動化（読み込み優先順: OS 環境 > .env.local > .env）。
  - プロジェクトルート自動検出ロジックを実装（.git または pyproject.toml を探索）。
  - .env パーサを実装（コメント、`export KEY=val`、シングル/ダブルクォート、バックスラッシュエスケープ対応、インラインコメント処理など）。
  - 読み込み時に既存 OS 環境変数を保護する仕組みを導入（protected set）。
  - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途等）。
  - Settings クラスを提供し、必須値取得時に _require が未設定で ValueError を発生させる。
  - 設定プロパティ（J-Quants / kabu API / Slack / DB パス / 環境・ログレベル判定）を実装。env 値の検証（有効値集合チェック）を行うユーティリティを提供。

- AI ニュース解析（kabusys.ai.news_nlp）
  - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを取得して ai_scores テーブルへ保存する機能を実装。
  - ニュースウィンドウ計算（JST 前日 15:00 ～ 当日 08:30 に対応、内部は UTC naive datetime で扱う calc_news_window を提供）。
  - バッチ処理（1 API コールあたり最大 20 銘柄）と 1 銘柄あたり記事数/文字数の上限（記事数最大 10 件、文字数 3000 文字でトリム）を実装。
  - OpenAI 呼び出しは JSON mode（response_format）を使用し、レスポンスの厳格なバリデーションを実装（results 配列・code/score 検査・数値チェック・既知コードのみ採用）。
  - 429 / ネットワーク断 / タイムアウト / 5xx を対象とした指数バックオフリトライ（最大リトライ数）を実装。その他エラーはスキップして処理継続（フェイルセーフ）。
  - スコアは ±1.0 にクリップし、取得に成功した銘柄のみを ai_scores テーブルへ置換的に書き込む（DELETE → INSERT、部分失敗時に既存データ保護）。
  - テスト容易性を考慮して、内部の OpenAI 呼び出し関数を patch で差し替え可能に設計。

- AI レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する機能を実装。
  - ma200_ratio 計算（target_date 未満のデータのみ使用しルックアヘッドバイアスを回避）。
  - マクロキーワードで raw_news をフィルタしてタイトルを収集し、LLM（gpt-4o-mini）で macro_sentiment を取得。API 失敗時は macro_sentiment=0.0 のフェイルセーフ。
  - レジームスコア合成ロジック（クリップ、閾値に基づくラベリング）を実装。
  - market_regime テーブルへは冪等的に書き込み（BEGIN / DELETE WHERE date=? / INSERT / COMMIT、失敗時は ROLLBACK）。
  - OpenAI 呼び出しは独立実装でモジュール結合を避け、リトライ・エラー処理を備える。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research モジュールで以下のファクターを実装:
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。データ不足時は None を返す。
    - Volatility / Liquidity: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比率（volume_ratio）。
    - Value: PER（price / EPS、EPS=0/欠損は None）、ROE（raw_financials からの取得）。
  - DuckDB 上の SQL + ウィンドウ関数で実装し、prices_daily / raw_financials のみ参照する非破壊設計。
  - 結果は (date, code) を含む dict のリストで返却。

  - feature_exploration モジュールで以下を実装:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons の検証（正の整数、<=252）。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算。有効レコードが 3 件未満の場合は None。
    - rank: 同順位は平均ランクにするランク関数（丸めで ties 検出の堅牢化）。
    - factor_summary: 各ファクター列について count/mean/std/min/max/median を返す統計サマリ。

- データ基盤（kabusys.data）
  - calendar_management:
    - market_calendar を参照する営業日判定ユーティリティを実装（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB にカレンダーが無い場合は曜日ベース（平日判定）でフォールバックする一貫性のある実装。
    - calendar_update_job を提供し、J-Quants クライアントから差分取得 → 保存（バックフィル・健全性チェックを含む）。
    - 複数の安全措置（最大探索日数・バックフィル日数・将来日付の健全性チェック）を実装。

  - pipeline:
    - ETLResult データクラスを公開（ETL の取得件数、保存件数、品質チェック結果、エラー一覧などを保持）。
    - テーブル存在チェックや最大日付取得ユーティリティを実装。
    - ETL の設計方針（差分取得、バックフィル、品質チェックを継続的に行う）が明示されている。

  - etl モジュールで ETLResult を再エクスポート。

### 変更
- （初回リリースのため既存バージョンからの差分はなし）

### 修正
- （初回リリースのため修正の記録なし）

### セキュリティ
- OpenAI API キー未設定時は明確に ValueError を投げることで誤った静默失敗を避ける実装。
- .env ファイル読み込みは OS 環境変数の上書きを保護する仕組みを提供（protected set）。

### 設計上の重要な注意点（ドキュメント的記載）
- ルックアヘッドバイアス防止:
  - news_nlp / regime_detector / research モジュールはいずれも内部で datetime.today() / date.today() を参照せず、呼び出し側から target_date を受け取る設計。
  - DB クエリは target_date 未満または target_date を基準にリード/ラグを用いることで未来データ参照を回避。
- OpenAI 呼び出し:
  - gpt-4o-mini を想定、JSON mode を利用した厳格なパース・バリデーションを実施。
  - リトライ戦略（指数バックオフ）を実装し、特定のエラーはフェイルセーフで 0.0（センチメント）やスキップにフォールバック。
- DuckDB との互換性配慮:
  - executemany に対して空リストを渡さないガード（DuckDB 0.10 の制約を考慮）。
  - SQL は互換性に配慮した実装（ROW_NUMBER で最新財務を取得等）。
- 冪等性:
  - ETL / calendar_update_job / score_regime / score_news の DB 書き込みは冪等的に扱う（DELETE→INSERT / ON CONFLICT 更新等）設計。

注: 上記は提供されたソースコードからの推測に基づく CHANGELOG です。実際のリリース日・追加の変更や修正はリポジトリのコミット履歴をご確認ください。