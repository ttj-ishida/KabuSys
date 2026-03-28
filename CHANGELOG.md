# CHANGELOG

すべての変更は Keep a Changelog の仕様に従って記載しています。  
このプロジェクトはセマンティックバージョニングに従っています。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買システムのコアライブラリを追加。

### Added
- パッケージ基礎
  - kabusys パッケージの初期バージョンを追加。バージョンは `0.1.0`。
  - パッケージの公開モジュールセットを `__all__ = ["data", "strategy", "execution", "monitoring"]` として定義。

- 環境設定・ローダー（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先順: OS 環境変数 > .env.local > .env
    - プロジェクトルート検出ロジック: `.git` または `pyproject.toml` を基準に親ディレクトリを探索（CWD 非依存）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能（テスト用途）。
  - .env パーサー実装:
    - コメント行・空行スキップ、`export KEY=val` 形式対応、クォート文字とバックスラッシュエスケープ処理、インラインコメント解析（クォート有無で挙動を分離）。
  - .env 読み込み時の上書き/保護ロジック:
    - override フラグと protected キーセット（OS 環境変数保護）に対応。
  - Settings クラスを提供（settings インスタンスをエクスポート）:
    - J-Quants / kabu API / Slack / DB パス等の設定プロパティを用意。
    - 必須値取得時の検証（未設定時は ValueError）。
    - 環境（development/paper_trading/live）やログレベルの値検証。
    - パスは Path 型で返却（展開済み）。

- AI モジュール（kabusys.ai）
  - news_nlp（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出し、ai_scores テーブルへ永続化する処理を実装。
    - 主な機能:
      - タイムウィンドウ計算（前日15:00 JST〜当日08:30 JST を UTC に変換）
      - 銘柄ごとに最新記事を集約（記事数・文字数に上限）
      - 最大 20 銘柄単位でバッチ送信
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ
      - レスポンスの厳密な JSON 検証（結果バリデーション）とスコアクリップ（±1.0）
      - 取得成功分のみを DELETE → INSERT で置換して部分失敗時のデータ保護を実現
    - テスト容易性: OpenAI 呼び出し部分を内部関数で分離（パッチ可能）
  - regime_detector（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（70%）とニュース LLM センチメント（30%）を合成して日次市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ保存する処理を実装。
    - 主な機能:
      - ma200_ratio 計算（target_date 未満のデータのみ使用、データ不足時は中立扱い）
      - マクロキーワードで raw_news をフィルタしてタイトルを抽出
      - OpenAI（gpt-4o-mini）でマクロセンチメント評価（記事が無ければ LLM 呼び出しをスキップし 0.0 を採用）
      - API エラー時のリトライ（指数バックオフ）、最終的な失敗は macro_sentiment=0.0 にフォールバック
      - レジームスコア合成・ラベル判定・冪等的 DB 書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）
    - テスト容易性: OpenAI 呼び出し部分は別実装でパッチ可能

- Data モジュール（kabusys.data）
  - calendar_management
    - JPX カレンダー管理（market_calendar）と営業日判定ユーティリティを実装。
    - 提供関数:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - 実装上の特長:
      - DB に登録があればその値を優先、未登録日は曜日ベースでフォールバック（週末のみ非営業日扱い）
      - 最大探索日数制限で無限ループを防止
      - calendar_update_job: J-Quants API から差分取得して冪等保存（バックフィル、健全性チェック、例外ハンドリング）
  - pipeline（kabusys.data.pipeline）
    - ETL パイプラインの基礎（差分取得、保存、品質チェックの呼び出し）を実装するためのユーティリティを追加。
    - ETLResult データクラスを定義（target_date, fetched/saved 件数、quality_issues、errors 等を収集）し、監査・ログ用に辞書化メソッドを提供。
    - テーブル存在チェックや最大日付取得等の内部ユーティリティを提供。
  - etl から ETLResult を再エクスポート。

- Research モジュール（kabusys.research）
  - factor_research
    - ファクター計算ユーティリティを実装（prices_daily / raw_financials のみ参照、DBのみで計算）。
    - 提供関数:
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（データ不足時は None）
      - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio（ウィンドウ不足は None）
      - calc_value: per / roe（最新財務データを target_date 以前から取得）
    - 各関数は SQL + Python で効率的に計算（ウィンドウ/ラグ等を DuckDB のウィンドウ関数で実装）
  - feature_exploration
    - 研究用途の統計ユーティリティを実装。
    - 提供関数:
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算
      - calc_ic: スピアマンのランク相関（Information Coefficient）計算
      - rank: 同順位は平均ランクで扱うランク化ユーティリティ（丸めにより ties の検出漏れを防止）
      - factor_summary: count/mean/std/min/max/median を計算する統計サマリー
  - data.stats の zscore_normalize を再エクスポートして研究用 API を統合

### Changed
- 設計方針・堅牢性の強化（全体）
  - ルックアヘッドバイアス防止のため、主要な処理（news / regime / research / ETL 等）で datetime.today()/date.today() の直接参照を避け、呼び出し側から target_date を渡す設計を採用。
  - 外部 API 呼び出し時はフェイルセーフを採用（API 失敗時に例外をそのまま投げずにフォールバックや部分スキップにより処理継続）。
  - DB 書き込みは可能な限り冪等に（DELETE → INSERT 等）し、トランザクション制御（BEGIN/COMMIT/ROLLBACK）を実装。
  - DuckDB の互換性（executemany に空リストを渡せない等）を考慮した実装。

### Fixed
- 設定/入力パースの堅牢性改善
  - .env パーサーでのクォート内エスケープやインラインコメントの扱いを正確化し、実運用での多様な .env 書式に耐えるように修正（初期実装として安定化）。
  - OpenAI 回答の JSON パースの耐性を強化（前後の余計なテキストを含む場合は最外の {} を抽出して復元を試みる）。

### Security
- API キー・機密情報の取り扱い
  - Settings は必須の環境変数を明示的に検証し、未設定時に早期エラー（ValueError）を発生させることで誤った実行を防止。
  - .env 自動読み込みは環境変数で明示的に無効化可能（テストや CI 用: KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

注記:
- 本 CHANGELOG はコードベースから自動的に推測して作成しています。実装の詳細や挙動は該当ソースコードおよびドキュメント（DataPlatform.md / StrategyModel.md 等）を参照してください。