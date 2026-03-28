# Changelog

すべての重要な変更はこのファイルに記載します。本ファイルは Keep a Changelog のフォーマットに準拠します。

フォーマット: [version] - YYYY-MM-DD

## [Unreleased]
- なし

## [0.1.0] - 2026-03-28
初期リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
  - パッケージ公開 API として data / research / ai 等のモジュールを __all__ で整理。

- 設定管理 (kabusys.config)
  - .env / .env.local の自動ロード処理を実装（プロジェクトルートは .git または pyproject.toml で探索、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env 行パーサ（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）を実装。
  - OS 環境変数を保護する `protected` 機構、読み込み順序（OS > .env.local > .env）に対応。
  - Settings クラスを導入し、J-Quants / kabuAPI / Slack / DB パス / ログレベル / 動作環境などのプロパティを提供。未設定の必須環境変数は明確な ValueError を発生させる。

- AI モジュール (kabusys.ai)
  - news_nlp モジュール
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）に JSON mode で投げてセンチメント（ai_scores）を算出・保存する処理を実装。
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたりの記事数・文字数上限（トリム）対応。
    - レート制限 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。リトライ上限を設定し、失敗時は当該チャンクをスキップして処理継続（フェイルセーフ）。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code/score 型チェック、未知コードの無視、スコアの有限性検査）、スコアを ±1.0 にクリップ。
    - DB 書き込みは冪等性を考慮（該当 date/code を先に DELETE してから INSERT、部分失敗時に既存スコアを保護）。
    - テスト容易性のため API 呼び出し関数を patch で差し替え可能。

  - regime_detector モジュール
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次マーケットレジームを判定（'bull' / 'neutral' / 'bear'）。
    - ma200_ratio の計算は target_date 未満のデータのみを使用し、データ不足時は中立扱い（1.0）で WARNING ログ出力。
    - マクロニュース抽出用のキーワードリストと最大記事数制限を実装し、記事がない場合は LLM 呼出しを省略して macro_sentiment=0.0 とするフェイルセーフ。
    - OpenAI 呼び出し時のリトライとエラーハンドリング（RateLimit/接続/タイムアウト/5xx）、JSON パース失敗時は macro_sentiment=0.0 にフォールバック。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - テスト容易性のため api_key を引数で注入可能。内部で datetime.today() を参照しない設計（ルックアヘッドバイアス回避）。

- Data モジュール (kabusys.data)
  - calendar_management
    - market_calendar を用いた営業日判定ロジック（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）を実装。
    - market_calendar 未取得時は曜日ベース（土日非営業）でフォールバックする一貫した挙動を提供。
    - 最大探索範囲制限で無限ループを防止。DB に NULL がある場合のログ警告など堅牢性を考慮。
    - calendar_update_job: J-Quants API（jquants_client）から差分取得・バックフィル（直近数日を再取得）・ON CONFLICT 型の冪等保存を行う夜間バッチ処理を実装。健全性チェック（将来日付の異常検出）を追加。

  - pipeline / etl
    - ETL パイプライン設計に基づくユーティリティと ETLResult データクラスを実装。
    - ETLResult は処理結果（取得/保存件数、品質問題リスト、エラーリスト）を格納し、has_errors / has_quality_errors / to_dict を提供。
    - テーブル存在チェックや最大日付取得等の内部ユーティリティを実装。
    - etl モジュールから ETLResult を再エクスポート。

- Research モジュール (kabusys.research)
  - factor_research
    - Momentum: mom_1m / mom_3m / mom_6m（営業日ベースのラグ）と ma200_dev（200日移動平均乖離）計算を実装。データ不足銘柄は None を返す。
    - Volatility: 20日 ATR（true range 計算）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を実装。ATR の NULL 伝播を考慮。
    - Value: raw_financials から target_date 以前の最新財務データを取得して PER / ROE を計算。EPS 欠損や 0 の場合は None。
    - すべて DuckDB 上の SQL（および一部 Python）で完結する設計。

  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD を用いて一括取得。ホライズンのバリデーション（1..252）とスキャン範囲の最小化を実装。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を実装。データ不足時は None。
    - rank: 同順位の平均ランク処理（丸めによる ties の検出回避）。
    - factor_summary: count/mean/std/min/max/median を計算する統計要約。

### Changed
- 設計上の方針を明示
  - 多くのモジュールで「datetime.today()/date.today() を直接参照しない」設計を採用し、ルックアヘッドバイアスを防止。
  - DuckDB をデータ処理基盤として想定し、SQL ウィンドウ関数や executemany の互換性制約（空リスト不可等）に対応した実装。

### Security
- 環境変数読み込みで OS 環境変数を保護する仕組み（.env が OS 環境を上書きしない既定挙動、および protected set）を導入。

### Fixed
- 該当なし（初期リリースにつきバグ修正ログはなし）。

### Removed / Deprecated
- 該当なし。

---

注:
- 本 CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノートやコミット履歴と差異がある場合があります。テストや運用時の細かい挙動（例: jquants_client の具体的実装、DB スキーマの詳細等）は別途ドキュメント / マイグレーションで補完してください。