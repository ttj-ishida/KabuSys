CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは Keep a Changelog に準拠します。
リリースは日付順（降順）で記載しています。

[0.1.0] - 2026-04-03
-------------------

Added
- 初回公開リリース。日本株自動売買支援ライブラリ「KabuSys」を追加。
- パッケージメタ情報
  - パッケージバージョン: 0.1.0
  - パッケージトップ: src/kabusys/__init__.py（data, strategy, execution, monitoring を公開）
- 環境変数／設定管理（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定を自動ロード（プロジェクトルートを .git / pyproject.toml から自動検出）。
  - 読み込み優先順位: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env のパース機能を実装（export KEY=val 形式対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理）。
  - 設定アクセス用 Settings クラスを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 実行環境識別など）。
  - 環境変数の必須チェック（_require）と値バリデーション（KABUSYS_ENV, LOG_LEVEL）。
- AI モジュール（src/kabusys/ai）
  - ニュースセンチメントスコアリング（news_nlp.score_news）
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄単位のセンチメントを算出。
    - チャンク処理（最大 20 銘柄/コール）、1銘柄あたり記事数・文字数上限、JSON Mode レスポンス検証。
    - レート制限・ネットワーク断・タイムアウト・5xx 対応の指数バックオフリトライ。
    - DuckDB への冪等書き込み（DELETE → INSERT）と部分失敗時の他データ保護。
    - テスト用に API 呼び出しを差し替え可能（_call_openai_api の patch を想定）。
  - 市場レジーム判定（regime_detector.score_regime）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次レジームを判定（bull / neutral / bear）。
    - OpenAI 呼び出しのリトライ・エラー扱いのフォールバック（失敗時は macro_sentiment=0.0）。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
- Data モジュール（src/kabusys/data）
  - マーケットカレンダー管理（calendar_management）
    - market_calendar に基づく営業日判定、next/prev_trading_day、get_trading_days、is_sq_day を提供。
    - DB にデータがない／未登録日には曜日ベースのフォールバック（週末を非営業日とする）を採用。
    - JPX カレンダーを J-Quants から差分取得する夜間バッチ job（calendar_update_job）を実装。バックフィル・健全性チェックあり。
  - ETL パイプラインインターフェース（etl.py と pipeline.ETLResult）
    - ETL 実行結果を表す ETLResult データクラス（取得数・保存数・品質問題・エラーリスト等）を公開。
  - パイプライン実装（pipeline）
    - 差分更新ロジック、バックフィル、品質チェックとの連携を想定した設計。
    - DuckDB 存在確認・最大日付取得等のユーティリティを実装。
- Research モジュール（src/kabusys/research）
  - ファクター計算（factor_research）
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高変化率）、バリュー（PER/ROE）を計算する関数を提供（DuckDB SQL ベース）。
    - データ不足時の None 処理やログ出力を考慮。
  - 特徴量探索（feature_exploration）
    - 将来リターン算出（calc_forward_returns、複数ホライズン対応・入力検証あり）。
    - IC（Information Coefficient）算出（スピアマンのρ、ランク化ユーティリティ rank）。
    - ファクター統計サマリー（count/mean/std/min/max/median）。
  - zscore_normalize を data.stats から再公開（モジュール統合用）。
- 一般的な設計方針・安全策
  - ルックアヘッドバイアス防止のため、各処理は datetime.today()/date.today() を直接参照しない（target_date を引数で明示）。
  - OpenAI API キーは関数引数で注入可能（テスト容易性）。引数未指定時は環境変数 OPENAI_API_KEY を参照。
  - DuckDB のバージョン差分に配慮した実装（executemany の空リスト回避、list バインドの安定性対策）。
  - API 呼び出しのフェイルセーフ: 失敗しても例外をそのまま投げず、フォールバック値で継続する箇所あり（ログ出力）。
  - ロギングを随所に実装し、失敗時やデータ不足時にわかりやすい警告/情報を出力。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 環境変数ロード時に既存 OS 環境変数を保護する仕組み（protected set）を導入。  
  .env を override する際も OS 環境変数の保護が可能。

Notes / 注意事項
- 本リリースは基盤ライブラリ実装フェーズの初版です。実行時には DuckDB と OpenAI SDK（および必要な外部ライブラリ）の適切なセットアップが必要です。
- OpenAI 呼び出しは gpt-4o-mini モデル・JSON Mode を利用する想定です。API 料金とレートリミットに注意してください。
- 実際の売買ロジック・注文発注周り（strategy / execution / monitoring の実装）は、このリポジトリに含まれるモジュール群との連携を前提に拡張してください。

--------- 

（補足）
- この CHANGELOG はコードベースの現状から推測して作成しています。実際のリリースノート作成時は、追加の変更点やバージョン方針に合わせて更新してください。