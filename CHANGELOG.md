Keep a Changelogに準拠した CHANGELOG.md（日本語）を以下に作成しました。コードから推測できる実装内容・設計方針を反映しています。

CHANGELOG.md
-------------

未訳注: 本ファイルは Keep a Changelog の形式に従い、プロジェクトの注目すべき変更点を記録します。

## [0.1.0] - 2026-04-03

### Added
- パッケージ初期リリース: kabusys (バージョン 0.1.0)
  - パッケージ公開情報:
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を定義。
    - パッケージの公開モジュール: data, strategy, execution, monitoring を __all__ に設定。

- 環境設定管理:
  - src/kabusys/config.py
    - .env(.local) の自動読み込み機構を実装（プロジェクトルート検出: .git または pyproject.toml）。
    - .env パーサを実装（コメント、export 形式、シングル/ダブルクォート、バックスラッシュエスケープ処理対応）。
    - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - OS 環境変数の保護（protected set）と override の扱い。
    - Settings クラスを提供し、各種設定値を環境変数から取得（J-Quants / kabuステーション / LINE / DB パス / 監視・閾値 / 実行環境判定など）。
    - env と log_level の検証（許容値チェック）、is_live/is_paper/is_dev ヘルパーを実装。
    - 必須環境変数未設定時に明示的に ValueError を送出する _require() 実装。

- AI 関連（OpenAI 統合: gpt-4o-mini を想定）:
  - src/kabusys/ai/news_nlp.py
    - ニュース記事の銘柄別センチメント自動スコアリング機能を実装。
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST 相当）の計算 calc_news_window。
    - raw_news と news_symbols から銘柄ごとに記事を集約して最大記事数/文字数でトリミング。
    - OpenAI へのバッチ送信（チャンク: 最大 20 銘柄）・JSON mode レスポンス処理。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ実装。
    - レスポンス検証（JSON パース、results キー、コード/スコア型検査、スコアの有限性検証）と ±1.0 のクリップ。
    - DuckDB に対する冪等書き込み（DELETE → INSERT、executemany の空リスト回避）。
    - テスト用フック: _call_openai_api を patch 可能に設計。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定する機能を実装。
    - ma200_ratio 計算（ルックアヘッドバイアス防止のため target_date 未満のデータのみ使用、データ不足時は中立値 1.0 を採用）。
    - マクロキー ワードによる raw_news フィルタリングと最大記事件数制限。
    - OpenAI 呼び出し（JSON mode）とリトライ戦略、API失敗時は macro_sentiment=0.0 にフォールバック。
    - 判定スコア合成・閾値によるラベル付け・market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - tests 用に _call_openai_api を patch 可能に設計（news_nlp と独立した実装でモジュール結合を避ける）。

- データプラットフォーム / ETL:
  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETLResult データクラスを追加（取得件数・保存件数・品質問題・エラーメッセージ等の集計）。
    - 差分更新、バックフィル、品質チェックのための設計方針・ユーティリティを実装（J-Quants クライアント連携を想定）。
    - DuckDB テーブル存在チェック、最大日付取得用ユーティリティを実装（後続 ETL ロジック向けに整備）。
    - ETLResult.to_dict() で品質問題をシリアライズ可能に実装。

  - src/kabusys/data/calendar_management.py
    - JPX マーケットカレンダー管理（market_calendar テーブル）を実装。
    - 営業日判定 API: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - DB のデータがない場合の曜日ベースフォールバック（週末を非営業日扱い）。
    - calendar_update_job: J-Quants からの差分取得、バックフィル、健全性チェック、save (jq.save_market_calendar) 呼び出しと保存件数の返却。
    - maximum search 範囲 (_MAX_SEARCH_DAYS) による無限ループ防止、直近バックフィル日数、先読み日数等の定数化。

- リサーチ / ファクター計算:
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M、ma200乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER、ROE）を DuckDB 上の SQL で計算する関数群を実装。
    - SQL ではウィンドウ関数を活用し、データ不足時は None を返す設計。
    - 関数: calc_momentum, calc_volatility, calc_value。全て prices_daily / raw_financials を参照する形で設計。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns（複数ホライズンの一括取得、ホライズンのバリデーションと範囲スキャン最適化）。
    - IC（Information Coefficient）計算 calc_ic（Spearman ランク相関、必要件数未満の場合 None）。
    - rank ユーティリティ（同順位は平均ランク、丸めで ties の検出漏れを防止）。
    - factor_summary：count/mean/std/min/max/median の集計を標準ライブラリで実装（pandas 非依存）。

- データアクセスまわり:
  - src/kabusys/data/__init__.py と etl/pipeline の公開整備（ETLResult を再エクスポート）。

### Changed
- （初回リリースのため本バージョンにおける「変更」はなし。実装時の設計判断や既定値は上記 Added に記載）

### Fixed
- （初回リリースのため本バージョンにおける「修正」はなし）

### Security
- OpenAI API キーは引数で注入可能（api_key）かつ環境変数 OPENAI_API_KEY を参照する設計。必須未設定時は明示的に ValueError を発生させることで誤った無認証呼び出しを防止。

注記 / 設計上の重要ポイント
- ルックアヘッドバイアス対策: いずれのモジュールも datetime.today()/date.today() を直接参照せず、外部から与えられた target_date を基準に計算する設計。
- DuckDB を想定したクエリ最適化と互換性対策（executemany の空リスト回避など）。
- OpenAI 呼び出しは JSON Mode（response_format={"type":"json_object"}）を想定し、厳格なレスポンス検証を行う。レスポンスパース失敗や API エラー時はフェイルセーフで継続（0 スコアやスキップ）する方針。
- テスト容易性: API 呼び出し用内部関数（_call_openai_api 等）を patch 可能にして単体テストで差し替えられるようにしている。
- 環境変数自動ロードはプロジェクトルート検出に基づくため、配布後も安全に動作。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。

今後の予定（想定）
- strategy / execution / monitoring の具体実装（本リリースではパッケージ公開名のみ）。
- jquants_client の具体実装と ETL pipeline のエンドツーエンド動作確認。
- テストカバレッジ拡充と CI ワークフローの整備。
- ドキュメント（API 仕様、運用手順、環境構築手順）の追加。

-----