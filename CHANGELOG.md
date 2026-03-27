# CHANGELOG

すべての注目すべき変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

- フォーマット: https://keepachangelog.com/ja/1.0.0/
- 日付はコミット/リリース時点で推定しています（コード内容に基づく推測）。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-27
初回リリース。以下の主要機能・モジュールを実装しています。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開。__version__ = 0.1.0。公開 API として data, research, ai 等をエクスポート。

- 設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を起点に探索）。
  - 環境変数自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト向け等）。
  - .env パース機能の強化:
    - `export KEY=val` 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープに対応。
    - クォートなしの行でのインラインコメント処理（直前が空白/タブの場合に # をコメントとみなす）。
  - protected オプションを使用した .env 上書き制御（OS 環境変数保護）。
  - Settings クラスを提供（J-Quants / kabu / Slack / DB パス / 環境設定等のプロパティ: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL）。
  - env/log_level の妥当性検証（development / paper_trading / live、DEBUG 等のログレベル）。

- AI モジュール (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - score_news(conn, target_date, api_key=None): raw_news と news_symbols を元に銘柄ごとのセンチメント ai_score を生成して ai_scores テーブルへ書き込む。
    - ニュース時間ウィンドウ定義（JST 前日 15:00 ～ 当日 08:30 を UTC に変換して比較）。
    - 銘柄ごとに記事を集約（最大記事数・文字数でトリム）。
    - バッチ送信（1 API コールで最大 20 銘柄）と JSON Mode を用いた OpenAI 連携（gpt-4o-mini）。
    - 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。
    - レスポンスの厳密なバリデーション（results リスト、code と score、未知コードは無視、スコアを ±1.0 にクリップ）。
    - DuckDB に対する冪等的な書き込み（該当 date/code の DELETE → INSERT）。DuckDB 0.10 の executemany 空リスト制約への対応。
    - テストしやすさのため _call_openai_api を patch で差し替え可能。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日移動平均乖離とマクロニュースの LLM センチメントを重み合成（70%:MA, 30%:macro）して market_regime テーブルへ冪等書き込み。
    - ma200_ratio の計算時にルックアヘッドを避ける（target_date 未満のデータのみ使用）およびデータ不足時のフェイルセーフ（中立=1.0）。
    - マクロニュースはキーワードでフィルタして件数上限を設定し、記事がない場合は LLM 呼出しをスキップして macro_sentiment=0.0。
    - OpenAI への呼び出しでのリトライ戦略、API 失敗やパース失敗時は 0.0 にフォールバックして継続。
    - レジームスコアを [-1.0, 1.0] にクリップし、閾値で bull/neutral/bear を判定。

- データプラットフォーム (kabusys.data)
  - calendar_management
    - JPX カレンダー管理のユーティリティ（market_calendar テーブルに基づく営業日判定）。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days API を提供。
    - market_calendar が未存在・未登録日の場合は曜日ベース（土日非営業日）でフォールバックする一貫した挙動。
    - calendar_update_job: J-Quants API（jquants_client 経由）から差分取得して market_calendar を冪等更新。バックフィル、健全性チェック（未来日付の異常検出）を実装。
  - pipeline（ETL）
    - ETLResult データクラスを公開（取得件数、保存件数、品質チェック結果、エラー一覧などを保持）。
    - 差分取得・バックフィル・品質チェックの設計に対応するユーティリティを実装。
    - DuckDB の存在確認や最大日付取得などの内部ユーティリティを実装。

- リサーチモジュール (kabusys.research)
  - factor_research: calc_momentum / calc_volatility / calc_value を実装
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
    - Volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率（データ不足は None）。
    - Value: latest raw_financials から PER, ROE を計算（EPS が 0 または欠損は None）。PBR / 配当利回りは未実装として明示。
    - すべて DuckDB 上の prices_daily/raw_financials のみを参照し、外部 API を呼ばない設計。
  - feature_exploration: calc_forward_returns / calc_ic / rank / factor_summary を実装
    - 将来リターンの同時取得クエリ（複数ホライズンを一度に処理）。
    - Spearman ランク相関（IC）をランク平均処理で実装（ties は平均ランク）。
    - 統計サマリー（count, mean, std, min, max, median）を提供。
    - 外部ライブラリに依存せず純粋 Python + DuckDB で実装。

- DB/トランザクションの堅牢性
  - 明示的な BEGIN / DELETE / INSERT / COMMIT を用いた冪等書き込みパターン。
  - WRITE エラー時の ROLLBACK と警告ログ出力処理を実装（ROLLBACK に失敗した場合も警告ログを出す）。
  - DuckDB バインド/ executemany の互換性に配慮した実装。

- テスト支援
  - OpenAI 呼び出し部分は内部関数をモジュール内に実装し、テスト時に patch で差し替え可能（ユニットテスト容易性の向上）。

### 変更 (Changed)
- 初回リリースのため該当なし（初期実装）。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 廃止 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- OpenAI API キーの扱い:
  - score_news / score_regime は api_key 引数または環境変数 OPENAI_API_KEY を参照。
  - API キー未設定時は ValueError を発生させて明示的に失敗する（無音での API 呼び出しを防止）。
- .env の上書き制御により OS 環境変数の上書きを保護する設計。

### 既知の制限・今後の改善予定（コードから推測）
- raw_financials からの PBR や 配当利回りはまだ未実装（calc_value で注記あり）。
- 一部実装（例: pipeline._adjust_to_trading_day の詳細実装継続）がスニペット上で途中表現になっている箇所があるため、将来的に整備予定。
- OpenAI モデルの切替や rate-limit に対する更なる最適化（バッチサイズ・遅延戦略の調整）は将来の改善候補。
- jquants_client の具体的実装は別モジュールに依存しており、API のアップデートに応じた互換性対応が必要。
- 発注・実行（execution）やモニタリング周りはパッケージ API に含まれるが、本リリースではデータ処理・研究・AI スコアリングに重点を置いた実装。

---

（注）本 CHANGELOG は与えられたソースコードの内容から推測して作成しています。実際のコミット履歴やリリースノートが存在する場合はそれに合わせて更新してください。