CHANGELOG
=========
すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------
（今後の変更をここに記載します）

0.1.0 - 2026-04-02
-----------------
最初の公開リリース。主要な機能群とユーティリティを実装しています。

Added
- パッケージ基盤
  - パッケージ初期化: kabusys.__init__ にバージョン "0.1.0" と公開モジュール一覧を追加。
- 設定管理
  - kabusys.config:
    - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で探索）。
    - export KEY=val 形式やクォート・エスケープ、インラインコメント考慮など堅牢な .env パーサーを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / データベース / 監視 / ログ設定などの環境変数をプロパティとして公開。必須パラメータ未設定時に明確なエラーを投げる。
    - 環境値の検証（KABUSYS_ENV, LOG_LEVEL の候補チェック）と便利プロパティ（is_live / is_paper / is_dev）を追加。
- AI（ニュース NLP / レジーム検出）
  - kabusys.ai.news_nlp:
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON Mode）で銘柄別センチメントを算出して ai_scores テーブルへ書き込む機能を実装。
    - バッチ処理（最大20銘柄/チャンク）、トークン肥大化対策（記事件数・文字数制限）、レスポンスバリデーション、スコアクリップ（±1.0）を実装。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ、部分失敗時に他銘柄の既存データを保護する書き込み戦略（DELETE→INSERT）を実装。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能（_call_openai_api のモック）。
    - ニュース収集ウィンドウ calc_news_window を実装（JST ベースのウィンドウを UTC naive datetime に変換）。
  - kabusys.ai.regime_detector:
    - ETF 1321 の 200 日移動平均乖離（70%）とマクロセンチメント（30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出し market_regime テーブルへ冪等書き込みする機能を実装。
    - マクロニュース抽出、OpenAI 呼び出し（gpt-4o-mini）による JSON レスポンスパース、リトライ・フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアス防止の設計（date 引数ベース、datetime.today() を参照しない）を徹底。
- データプラットフォーム関連
  - kabusys.data.pipeline / kabusys.data.etl:
    - ETLResult データクラスを公開。ETL の取得数・保存数・品質チェック結果やエラーを集約する統一的な戻り値を提供。
    - 差分取得・バックフィル・品質チェックを想定した設計（Docstring に処理フローを明記）。
  - kabusys.data.calendar_management:
    - market_calendar を用いた営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - JPX カレンダーを J-Quants から取得して更新する calendar_update_job（バックフィル、健全性チェック、冪等保存）を実装。
    - DB未登録日に対する曜日ベースのフォールバックを用意し、DB がまばらな場合でも一貫した動作となる設計。
- リサーチ / ファクター
  - kabusys.research.factor_research:
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR 等）、Value（PER / ROE）などのファクター計算関数を実装。DuckDB の SQL とウィンドウ関数で効率的に計算。
    - データ不足時の挙動（必要行数未満は None）を明確に定義。
  - kabusys.research.feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランキング変換（rank）、統計サマリー（factor_summary）を実装。外部ライブラリに依存しない純 Python 実装。
- その他ユーティリティ
  - duckdb をデータ処理基盤として全面的に採用し、SQL + Python 混合で処理を実装。
  - ロギングを各モジュールに導入し、処理の経過や警告を出力。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数の上書き保護（protected set）を .env 読み込みロジックに追加し、OS 環境変数が意図せず上書きされないように保護。

Notes / 設計方針（抜粋）
- ルックアヘッドバイアス防止: 日次処理はすべて target_date 引数に基づき計算し、datetime.today()/date.today() を直接参照しない設計を採用。
- フェイルセーフ: 外部 API（OpenAI / J-Quants）失敗時は全停止せず、部分的にスキップしつつログ出力で可視化する方針。
- DB 書き込みは冪等性を重視（DELETE→INSERT、ON CONFLICT 想定）し、部分失敗時に既存データを極力保持する実装。
- テスト容易性: OpenAI 呼び出し等を差し替え可能にして単体テストを容易にするフックを備える。

今後の予定（例）
- モニタリング / 実行モジュール（execution / monitoring）の具体実装およびドキュメント化。
- ファクターの追加・改善、モデル検証用のバックテスト機能の追加。
- 運用向けのメトリクス / アラート統合（Slack 通知等）の強化。

----- 
（注）本 CHANGELOG は提供されたソースコード内容から推測して作成したもので、実際のコミット履歴に基づくものではありません。実際のリリース履歴や日付はプロジェクトの運用方針に合わせて調整してください。