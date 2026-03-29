# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に従っています。  
安定版リリースはセマンティックバージョニングに従います。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated/Removed/Security: 必要な場合に記載

## [0.1.0] - 2026-03-29

初回公開リリース。

### Added
- パッケージ基盤
  - kabusys パッケージの初期構成を追加。__version__ = 0.1.0。
  - モジュール公開: data, strategy, execution, monitoring をパッケージ API として公開。

- 設定・環境変数管理（kabusys.config）
  - .env/.env.local の自動読み込み機能を追加（プロジェクトルートは .git または pyproject.toml を探索して決定）。
  - .env パーサを実装（コメント行、export プレフィックス、引用符内エスケープ、インラインコメント扱いなどに対応）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（テスト用に自動読み込みを抑止可能）。
  - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス / 環境種別（development/paper_trading/live）/ログレベルの取得とバリデーションを実装。
  - 必須設定未定義時に ValueError を送出する _require ヘルパーを実装。

- AI（自然言語処理）機能（kabusys.ai）
  - ニュースセンチメント集計（kabusys.ai.news_nlp.score_news）
    - raw_news / news_symbols を銘柄ごとに集約し、OpenAI（gpt-4o-mini）を用いて銘柄別センチメントを算出、ai_scores テーブルへ書き込む。
    - バッチ処理（最大20銘柄/チャンク）、記事数・文字数トリム、JSON Mode 利用、レスポンスバリデーション、±1.0 でのクリップを実装。
    - リトライ（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ）、API失敗時はフェイルセーフでスキップして継続する設計。
    - テスト容易性のため OpenAI 呼び出しラッパーをパッチ差替え可能に実装。
    - DuckDB 互換性を考慮し、executemany に空リストを渡さない安全な DB 書込ロジックを実装（DELETE → INSERT の冪等置換）。
    - 時間ウィンドウ計算 util calc_news_window を提供（JST 指定のニュースウィンドウを UTC naive datetime で返す）。

  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
    - ETF 1321（Nikkei 225 連動）200日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して market_regime テーブルへ書き込み。
    - LLM 呼び出しは専用ラッパーで実行、API エラー時は macro_sentiment = 0.0 のフェイルセーフ。
    - DuckDB からのデータ取得はルックアヘッドバイアスを避けるため target_date 未満のデータのみを使用。
    - 冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を保証。

- データ管理（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを利用した営業日判定・探索ユーティリティを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - DB 登録データがない場合の曜日ベースのフォールバック（週末を非営業日）を実装し、DB がまばらでも一貫した挙動となるよう配慮。
    - calendar_update_job を実装し、J-Quants クライアント経由で差分取得・バックフィル・保存を行う。健全性チェック（遠すぎる last_date の検出）を実装。

  - ETL パイプライン（kabusys.data.pipeline / kabusys.data.etl）
    - ETLResult データクラスを導入し、ETL 実行結果・品質問題・エラーを構造化して返却可能に。
    - 差分更新、backfill、品質チェック（quality モジュール連携）の設計に沿ったヘルパーを実装。
    - data.etl で ETLResult を再エクスポート。

  - jquants_client と quality などの外部連携（実装は別モジュール想定）を利用するデータフロー基盤を提供。

- リサーチ機能（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム、ボラティリティ／流動性、バリュー系ファクターを計算する関数を追加:
      - calc_momentum（1M/3M/6M リターン、200日MA乖離）
      - calc_volatility（20日 ATR、相対ATR、平均売買代金、出来高比率）
      - calc_value（PER、ROE：raw_financials からの値を使用）
    - DuckDB SQL を活用して効率的に集計・ウィンドウ関数で算出。データ不足時は None を返す設計。

  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns（任意ホライズンの将来リターンを一括取得）
    - calc_ic（Spearman ランク相関で IC を計算）
    - rank（同順位は平均ランクに処理）
    - factor_summary（各カラムの count/mean/std/min/max/median を計算）
    - pandas 等に依存せず、純標準ライブラリ + DuckDB で完結する実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / 設計上の重要事項
- ルックアヘッドバイアス防止:
  - AI モジュール・リサーチモジュール・ETL 等、全体を通じて datetime.today() / date.today() を直接参照しない設計。target_date を明示的に渡すことで過去データのみを参照することを保証。
- DB 書き込みの冪等性:
  - market_regime, ai_scores 等へは既存レコードを DELETE してから INSERT することで置換挙動を実現。DuckDB の executemany に関する注意点（空リスト不可）に対する回避実装あり。
- OpenAI 呼び出しのロバスト性:
  - JSON パース失敗、API エラー、ネットワーク障害、レート制限に対するリトライ／フェイルセーフ（デフォルトで最大リトライ回数や待機時間を指定）。
  - テスト時に API 呼び出しを差し替えられるように内部ラッパーを用意。
- ロギング:
  - 主要処理（API 失敗、データ不足、パース失敗、ROLLBACK 失敗等）で詳細なログ出力を行う。
- 環境変数の取り扱い:
  - 必須環境変数未設定時は明確なエラーメッセージを出す（.env.example に基づく作成を促すメッセージ）。

### Breaking Changes
- 初回リリースのためなし。

### Migration / Upgrade Notes
- なし（初回リリース）。将来のリリースでは Settings API や DB スキーマの互換性に注意してください。

--- 

今後のリリースでは、テストカバレッジ強化、OpenAI モデル選択の柔軟化、ETL の並列化、モニタリング／アラート機能の追加等を予定しています。