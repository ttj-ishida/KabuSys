# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

全般:
- 初期リリース v0.1.0 を記録します。

## [Unreleased]

## [0.1.0] - 2026-04-02

### Added
- パッケージ初期導入
  - src/kabusys パッケージの基本構成を追加。バージョンは 0.1.0。
  - __all__ に "data", "strategy", "execution", "monitoring" を公開。

- 設定管理
  - src/kabusys/config.py:
    - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルート検出：.git または pyproject.toml を探索）。
    - export 形式やクォート・インラインコメントに対応した .env パース実装。
    - .env / .env.local の読み込み順序（OS 環境変数優先）と上書き保護（protected）を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
    - Settings クラスを追加（J-Quants・kabu API・Slack・DB パス・監視閾値・環境/ログレベル判定などのプロパティを提供）。必須環境変数未設定時に明示的なエラーを返す。

- AI（ニュース NLP / レジーム判定）
  - src/kabusys/ai/news_nlp.py:
    - raw_news / news_symbols を集約して銘柄ごとのニュースを OpenAI（gpt-4o-mini）でバッチ評価し、ai_scores テーブルへ書き込むスコアリングパイプラインを実装。
    - 時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST 相当）と記事トリム、バッチ処理（最大 20 銘柄/チャンク）、レスポンス検証、スコアクリップ（±1.0）、部分的書換え（DELETE→INSERT）などを実装。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライとフェイルセーフ（失敗時はスキップして継続）。
  - src/kabusys/ai/regime_detector.py:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出し、market_regime テーブルへ冪等書き込みする機能を実装。
    - マクロニュース抽出、OpenAI 呼び出し（JSON 出力期待）のリトライ・エラーハンドリング、フェイルセーフ（API 失敗時 macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアス回避のため日付取り扱いに注意（datetime.today() を直接参照しない設計）。

- リサーチ（ファクター・特徴量探索）
  - src/kabusys/research/factor_research.py:
    - Momentum / Volatility / Value / Liquidity 等の定量ファクター計算を実装（prices_daily / raw_financials を参照）。
    - calc_momentum, calc_volatility, calc_value を公開。200日 MA や ATR 等の計算・データ不足ハンドリングを含む。
  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
    - 外部ライブラリ非依存（標準ライブラリのみ）での実装と、入力検証（horizons の妥当性など）。

- データ基盤（カレンダー・ETL・パイプライン）
  - src/kabusys/data/calendar_management.py:
    - market_calendar を用いた営業日判定ユーティリティ群（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - データがない場合は曜日ベースのフォールバックを提供。最大探索日数の上限や健全性チェックを導入。
    - calendar_update_job を通じて J-Quants API から差分取得→冪等保存する夜間バッチ処理を実装（バックフィル・健全性チェック含む）。
  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py:
    - ETLResult データクラスを導入し ETL 結果の収集・シリアライズ（to_dict）機能を提供。
    - 差分更新の設計、品質チェック（quality モジュール連携）を想定したインターフェース。
    - etl モジュールは pipeline.ETLResult を再エクスポート。

- 互換性・DB（DuckDB）注意点
  - DuckDB のバージョン差を意識した実装（executemany の空リスト回避、list 型バインドの互換性回避など）。
  - DB 書き込みは冪等性・トランザクション（BEGIN/DELETE/INSERT/COMMIT / ROLLBACK ハンドリング）を重視。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- OpenAI API キーは引数で注入可能（テスト容易性）かつ環境変数 OPENAI_API_KEY を使用。未設定時は ValueError で明示的に通知。

### Notes / 設計上の留意点
- AI モジュールおよび一部のロジックはルックアヘッドバイアスを防ぐ設計（外部時刻の直接参照回避、DB クエリで date < target_date など）を採用。
- API 呼び出しに対してはリトライ・フォールバックを組み込み、外部サービス障害時でも全体処理が致命的に停止しないようにしている。
- ロギングを適切に出力し、異常時は詳細ログ（warning/exception）を残す実装。

<!--
フォーマット例（必要に応じてバージョン履歴を追加してください）:
[Unreleased]
[0.1.0] - 2026-04-02
-->
