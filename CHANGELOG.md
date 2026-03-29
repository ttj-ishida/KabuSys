# CHANGELOG

すべての重要な変更をここに記録します。フォーマットは Keep a Changelog に準拠しています。

- リリースノートは安定版リリースごとに記載しています。
- 目的：実装された機能、設計上の重要な決定、互換性や注意点を明確にすること。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回リリース。

### Added
- パッケージ基盤
  - kabusys パッケージ初期公開。__version__ = 0.1.0、主要サブパッケージ（data, research, ai, 等）を公開。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダ実装（プロジェクトルート探索: .git または pyproject.toml を基準）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD に対応。
  - .env パーサ実装:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。
    - クォートなし時のインラインコメント処理（先頭または直前が空白/タブの # をコメントとして扱う）。
    - 読み込み時の override / protected（OS 環境変数保護）オプション。
  - Settings クラスを実装（J-Quants / kabu ステーション / Slack / DB パス / 環境種別 / ログレベルなどをプロパティで取得）。
  - 環境値検証（KABUSYS_ENV、有効な LOG_LEVEL 値の検証、必須キー未設定時は ValueError を送出）。

- AI/NLP 周り（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - チャンク処理（デフォルトバッチサイズ 20 銘柄）・1銘柄あたりの最大記事数/文字数トリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - JSON Mode を利用した厳格なレスポンス期待と、JSON パースの回復処理（前後余剰テキストから {} を抽出して復元）。
    - リトライ戦略（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ）とフェイルセーフ（API 失敗時は該当チャンクをスキップし他銘柄処理継続）。
    - レスポンス検証ロジック（results リスト、code/score の型検査・既知コードのみ採用、スコアの有限性検査、±1.0 にクリップ）。
    - 書き込みは冪等性を考慮（対象コードのみ DELETE → INSERT して、部分失敗時に他コードの既存スコアを保護）。
    - テスト容易性: OpenAI 呼び出し箇所をモジュール内で差し替え可能（_call_openai_api を patch）。
    - 時間ウィンドウ計算関数 calc_news_window を提供（JST 基準の前日 15:00 〜 当日 08:30 に対応、DuckDB に対する UTC naive datetime を返す）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）と、ニュースベースのマクロセンチメント（重み 30%）を合成して market_regime テーブルに書き込む機能。
    - マクロニュース選別（マクロキーワード群）と LLM でのマクロセンチメント評価（gpt-4o-mini、JSON レスポンスを期待）。
    - LLM 呼び出しのリトライ・エラーハンドリング（API レベルの 5xx 判定、RateLimit 等のハンドリング）、API 失敗時は macro_sentiment=0.0 のフェイルセーフ。
    - 計算時にルックアヘッドバイアスを避ける設計（target_date 未満のデータのみ使用、datetime.today() を参照しない）。
    - market_regime への冪等書込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理。

- Data プラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー取得・更新の夜間バッチ calendar_update_job を実装（J-Quants から差分取得、バックフィル、健全性チェック、保存は jquants_client 経由で冪等保存）。
    - 営業日判定と関連ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - market_calendar が未取得の場合は曜日ベース（土日休）でフォールバックする設計。DB 登録がある場合は DB 値優先、未登録日は曜ベースで補完して next/prev と一貫した振る舞いを確保。
    - 最大探索範囲制限（_MAX_SEARCH_DAYS）・バックフィル日数・先読み日数・健全性チェック実装。
  - ETL パイプライン（kabusys.data.pipeline / kabusys.data.etl）
    - 差分取得・保存・品質チェックのための構造を実装（ETLResult データクラスを公開）。
    - ETLResult に取得件数・保存件数・品質問題（quality.QualityIssue）・エラーリストなどを格納し、has_errors / has_quality_errors / to_dict メソッドを提供。
    - DuckDB テーブル存在チェック・最大日付取得ユーティリティなどを実装。
    - 市場カレンダー調整ユーティリティ（_adjust_to_trading_day）など ETL 補助ロジックを実装（差分更新、backfill 指定可能）。
    - jquants_client と quality モジュールを利用する想定での連携ポイントを準備。

- Research（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）計算（DuckDB SQL による実装）。
    - Volatility / Liquidity（atr_20, atr_pct, avg_turnover, volume_ratio）計算（True Range 計算、ウィンドウ集計）。
    - Value ファクター（per, roe）: raw_financials から直近財務データを取得して計算。
    - 全関数は prices_daily / raw_financials テーブルのみ参照。データ不足時は None を返す設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算 calc_forward_returns（任意ホライズンのリターンを一括取得、ホライズン検証）。
    - IC（Information Coefficient）計算 calc_ic（Spearman ランク相関、同順位は平均ランク処理）。
    - ランク変換ユーティリティ rank（同順位の平均ランク、丸めにより ties の検出を堅牢化）。
    - 統計サマリー factor_summary（count/mean/std/min/max/median を計算）。
    - 実装は外部依存（pandas 等）に頼らず標準ライブラリと DuckDB SQL で完結。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （現時点で公開されているコードの範囲では特記事項なし。ただし OpenAI API キーや各種トークンは環境変数で管理し、.env の自動ロードは保護設定（protected）を考慮している。）

### Notes / Implementation decisions（重要な設計上の注意）
- ルックアヘッドバイアス対策:
  - AI モジュール、研究モジュール、ETL のいずれも内部で datetime.today() / date.today() を直接参照しない設計。必ず target_date を引数として受け取り、DB クエリは target_date 未満 / 前日に相当する範囲を明示的に指定する。
- OpenAI 統合:
  - gpt-4o-mini + JSON Mode を前提。レスポンスは厳密な JSON を期待するが、実際に前後に余分なテキストが付く場合を考慮した復元処理・検証ロジックを実装。
  - API 呼び出し箇所はテストでモック可能（_call_openai_api を patch）。
  - API エラーに対してはリトライ（指数バックオフ）およびフェイルセーフなフォールバックを用いる（例: macro_sentiment=0.0 や該当チャンクスキップ）。
- DuckDB 互換性:
  - DuckDB の executemany に空リストを渡せない制約に対応（事前チェック）。
  - SQL は DuckDB 環境を想定した実装（ROW_NUMBER / WINDOW / LEAD/LAG などを活用）。
- DB 書き込みの冪等性:
  - calendar_update_job, score_regime, score_news の書き込み部分は既存行を置換する（DELETE → INSERT、または ON CONFLICT を想定）ことで冪等性を意識した実装。
- ロギングとエラーハンドリング:
  - 失敗時に例外を投げるべき箇所（必須環境変数未設定、致命的な DB 書き込み失敗など）は明確に例外化し、API 呼び出しの失敗など運用上の一時的エラーはログに留めて処理継続するフェイルセーフ方針。
- テストフレンドリー:
  - OpenAI 呼び出しやファイル読み込み等の外部依存点はパッチしやすく設計（ユニットテストでの差し替えを想定）。

---

今後の予定（例）
- ai モデル評価やローカル代替案の追加（API 呼び出しコスト低減）。
- モニタリング・アラート機能の実装（Slack 通知などの統合）。
- ETL の品質チェック拡充と自動修復ルールの追加。

（必要に応じて、各リリース毎に上記フォーマットで変更点を追記してください。）