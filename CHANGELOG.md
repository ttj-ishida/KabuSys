# CHANGELOG

このプロジェクトは Keep a Changelog のフォーマットに従って変更履歴を管理します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

すべての日付はリリース日を示します。

## [0.1.0] - 2026-04-03

初回公開リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。

### 追加 (Added)
- パッケージ初期化
  - パッケージメタ情報および公開モジュールの定義を追加（kabusys.__init__、バージョン "0.1.0"）。
- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定値を読み込む自動ロード機能を実装。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応（テスト用）。
  - .env パース機能強化: export KEY=val 形式、シングル/ダブルクォート、エスケープ、インラインコメント処理などに対応。
  - 環境変数保護機構: OS 環境変数を protected として .env による上書きを制御。
  - Settings クラスを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境種別・ログレベル判定等のプロパティ）。
  - 必須環境変数未設定時は ValueError を送出する _require を実装。
- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を元に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）で銘柄単位のセンチメントを算出して ai_scores テーブルへ書き込む機能を実装。
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたりの最大記事数・最大文字数制限、レスポンスの厳密な JSON バリデーションを実装。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装。
    - API 未設定時は ValueError を送出。
    - 失敗時はフェイルセーフで当該チャンクをスキップし、他銘柄の既存スコアを消さないように部分的な DELETE → INSERT により置換。
    - calc_news_window 関数により、前日 15:00 JST ～ 当日 08:30 JST のウィンドウをUTCで扱う（ルックアヘッド回避）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定し market_regime テーブルへ冪等書き込みする処理を実装。
    - マクロキーワードで raw_news をフィルタして LLM に渡す仕組み、OpenAI 呼び出しのリトライ・エラーハンドリング、API 失敗時は macro_sentiment=0.0 とするフォールバックを実装。
    - ルックアヘッドバイアス防止の設計（target_date 未満のデータのみ使用、datetime.today() を参照しない）を遵守。
- データモジュール（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを実装（取得件数、保存件数、品質チェック結果、エラー一覧などを保持）。
    - jquants_client を通じた差分取得・保存・品質チェックのための基盤ロジックを実装（差分取得、backfill、品質検出の収集等を想定）。
    - ETLResult.to_dict により品質問題を辞書化して監査ログ等に利用可能。
    - pipeline 内ユーティリティ: テーブル存在確認、最大日付取得など（実装途中ファイル切れの箇所あり）。
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を用いた営業日判定ユーティリティを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - calendar_update_job による J-Quants からの差分取得と冪等保存（バックフィル、健全性チェックを含む）を実装。
    - market_calendar が未取得時の曜日ベース・フォールバックをサポート。
  - ETL の公開インターフェース（kabusys.data.etl）として ETLResult を再エクスポート。
- リサーチ機能（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、200日MA乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER、ROE）を DuckDB SQL ベースで実装。
    - データ不足時の None 処理、SQL ベースのウィンドウ集計により効率的に計算。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク関数（rank）、ファクター統計サマリー（factor_summary）を実装。
    - 外部ライブラリに依存せず標準ライブラリ・DuckDB のみで実装。
- 内部ユーティリティ・ログ
  - 各所で詳細なログ出力を追加（INFO/DEBUG/WARNING）。
  - DuckDB を主要なデータストアとして想定した実装。

### 変更 (Changed)
- （初回リリースにつき該当なし）

### 修正 (Fixed)
- （初回リリースにつき該当なし）

### セキュリティ (Security)
- OpenAI API キーや各種シークレットは Settings 経由で明示的に取得する設計。未設定時は明示的に例外を投げることで、誤った無認証実行を防止。

### 注意点 / 実装上の設計判断
- ルックアヘッドバイアスの防止を一貫して行う（datetime.today() を直接参照せず、target_date を明示的に渡す設計）。
- OpenAI など外部 API 呼び出しは失敗時にフェイルセーフ（0.0 フォールバックやチャンクスキップ）で処理を継続し、全体の可用性を優先。
- データベース書き込みは可能な限り冪等化（DELETE → INSERT、トランザクション）して部分失敗時の影響を限定。
- DuckDB のバージョン差異（executemany の空リストなど）を考慮した実装上の護りを入れている。

--- 

今後の予定（例）
- ETL pipeline の詳細メソッド完成・テスト、jquants_client の具体的な実装連携。
- モジュール別のユニットテストと CI 設定の追加。
- モデル・プロンプト改善、より詳細なログ・メトリクスの追加。

（必要があれば各モジュールごとの変更点をさらに細分化して追記します）