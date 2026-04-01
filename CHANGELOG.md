Keep a Changelog に準拠した変更履歴を以下に作成しました。コード内容から推測して記載しています。必要なら日付や文言の調整を行います。

CHANGELOG.md
============
全ての重要な変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  
https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
（このセクションは今後の変更のために予約しています）

[0.1.0] - 2026-04-01
-------------------
Added
- 初期リリース。KabuSys 日本株自動売買プラットフォームの基盤機能を提供するモジュール群を追加。
  - パッケージ初期化
    - kabusys.__version__ を "0.1.0" に設定し、主要サブパッケージ（data, research, ai, ...）を公開。
  - 環境設定（kabusys.config）
    - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で検索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env 行パーサ実装（export 句、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応）。
    - Settings クラスを追加し、J-Quants / kabuステーション / Slack / DB パス /監視閾値 / 環境（development/paper_trading/live）などを環境変数から取得・検証。
    - env/log_level の検証ロジックを実装（無効値は ValueError）。

  - AI モジュール（kabusys.ai）
    - ニュースセンチメントスコアリング（news_nlp.score_news）
      - 前日15:00 JST ～ 当日08:30 JST のニュースウィンドウを計算（UTC 換算）。
      - raw_news と news_symbols を集約し、銘柄ごとに複数記事をまとめて OpenAI（gpt-4o-mini）の JSON モードへバッチ送信。
      - バッチサイズ、最大記事数、最大文字数、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライを実装。
      - レスポンスの厳格な JSON バリデーションとスコア ±1.0 クリップ。
      - スコアは ai_scores テーブルへ冪等的に（DELETE → INSERT）書き込み、部分失敗時に既存の他銘柄スコアを保護。
      - DuckDB の executemany 空配列制約に対応したガードロジックを実装。
    - 市場レジーム判定（regime_detector.score_regime）
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
      - マクロセンチメントはマクロキーワードでフィルタした記事タイトルを OpenAI で評価。
      - API 呼び出しのリトライ（429/ネットワーク/タイムアウト/5xx）とフェイルセーフ（API 失敗時 macro_sentiment=0.0）。
      - DB への書き込みはトランザクションで冪等（BEGIN / DELETE / INSERT / COMMIT）し、失敗時は ROLLBACK を試行して例外を伝播。
      - ルックアヘッドバイアスを防ぐ設計（target_date 未満のみ参照、datetime.today() を参照しない）。
  - Data モジュール（kabusys.data）
    - マーケットカレンダー管理（calendar_management）
      - JPX カレンダーを扱うユーティリティ群を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
      - market_calendar が未取得の場合は曜日ベース（土日除外）でフォールバックする一貫したロジック。
      - next/prev_trading_day の最大探索日数制限（_MAX_SEARCH_DAYS）で無限ループを防止。
      - calendar_update_job を実装し、J-Quants からの差分取得 → 保存（バックフィル、健全性チェック含む）を行う。
    - ETL パイプライン（pipeline / etl）
      - ETLResult データクラスを提供し、ETL 実行結果（取得数、保存数、品質問題、エラー）を集約可能に。
      - 差分取得、バックフィル、品質チェック（quality モジュール利用）を想定した設計。
      - テーブル存在チェックや最大日付取得等のユーティリティを実装。
    - jquants_client のラッパー経由でのデータ取得・保存想定（実際のクライアントは別モジュール）。

  - Research モジュール（kabusys.research）
    - ファクター計算（factor_research）
      - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
      - Volatility: 20 日 ATR（atr_20）、ATR 比率（atr_pct）、20 日平均売買代金、出来高比率。
      - Value: per（株価 / EPS、EPS が 0 または欠損なら None）と roe（raw_financials から取得）。
      - 全関数は DuckDB と prices_daily / raw_financials のみ参照し、結果を (date, code) キーの辞書リストで返す。
    - 特徴量探索（feature_exploration）
      - 将来リターン計算（calc_forward_returns）：任意ホライズンのリターン（LEAD を使用）、horizons の妥当性チェック。
      - IC 計算（calc_ic）：スピアマンランク相関（ランクは同順位平均ランクに対応）を実装。十分なサンプルがない場合は None を返す。
      - 統計サマリー（factor_summary）：count/mean/std/min/max/median を算出。
      - ランク付けユーティリティ（rank）。
    - kabusys.data.stats の zscore_normalize を再エクスポート（research パッケージの一部として公開）。

Changed
- なし（初回リリースのため、既存変更はありません）。

Fixed
- なし（初回リリースのため、既存バグ修正履歴はありません）。ただし、実装内に以下の耐障害性対策あり:
  - OpenAI API 呼び出しでの各種エラーに対するリトライ/フォールバック（macro_sentiment=0.0 / スコア取得失敗時はスキップ）。
  - .env ファイル読込でのファイルオープン失敗時に警告を出して処理継続。
  - DB トランザクション失敗時に ROLLBACK を試行し、ROLLBACK 失敗は警告ログ出力。

Security
- 環境変数に API キーを期待する実装（OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN 等）。API キー未設定時は明示的なエラーを投げる箇所あり（安全な動作のための必須チェック）。

Notes / Known limitations
- DuckDB 依存: 多くのクエリは DuckDB に依存しており、DuckDB バージョン差分（例: executemany の空リスト挙動）に注意しているが、実行環境の DuckDB バージョンによっては追加調整が必要な場合があります。
- OpenAI 依存: gpt-4o-mini の JSON Mode を利用する前提。API の応答フォーマットや SDK バージョンの変化があるとパース側で影響を受ける可能性があるため、テストフック（内部の _call_openai_api のモック）が用意されています。
- ルックアヘッドバイアス対策: 多くの関数は datetime.today()/date.today() を直接参照せず、caller が target_date を明示的に渡す設計になっています。運用時は target_date の供給ミスに注意してください。
- 部分失敗の保護: ai_scores 書き込み等で「部分失敗時に他銘柄の既存スコアを消さない」設計を取っていますが、大規模トランザクションの途中失敗時の取り扱い（再実行ポリシー等）は運用ルールでのカバーが必要です。

開発者向け補足
- テスト容易性のため、OpenAI 呼び出し箇所（kabusys.ai の各モジュール）には _call_openai_api をパッチ/差し替え可能に実装しています（unittest.mock.patch による差し替えを想定）。
- .env 行パーサは export 構文やクォート内のバックスラッシュエスケープ、インラインコメント判定など現実的な .env の書き方に合わせた処理を実装しています。

今後の予定（推測）
- ai_scores / market_regime 等のテーブルスキーマ安定化と運用向けの監査ログ追加。
- ETL のスケジューリングと監視（Slack 通知等）機能の追加。
- 追加ファクターや特性探索の自動化、Backtest/Execution の統合強化。

---  
（以上）必要であれば、各モジュールごとの詳細な変更点やリリースノートの英文版を作成します。