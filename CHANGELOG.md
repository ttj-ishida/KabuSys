# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠します。  
このファイルはリポジトリの現在の状態（バージョン 0.1.0）からコードベースの主要な機能・設計方針を推測して記載しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-28
初回リリース。以下の主要機能とユーティリティを実装しています。

### 追加
- パッケージ基盤
  - パッケージのメタデータと公開モジュール定義を追加（kabusys.__init__）。公開モジュール候補に data, strategy, execution, monitoring を用意。
  - バージョン情報 __version__ = "0.1.0" を設定。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定値を読み込む自動ローダーを実装。
    - プロジェクトルートの検出は .git または pyproject.toml を基準に行い、CWD に依存しない実装。
    - 読み込み優先度：OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env のパーサーは以下に対応：
    - 空行・コメント（#）の無視
    - `export KEY=val` 形式のサポート
    - シングル/ダブルクォートとバックスラッシュエスケープの正しい処理
    - クォート無し値のインラインコメント処理（直前がスペース/タブの `#` をコメント扱い）
  - 既存 OS 環境変数を保護する protected オプション。override の制御で上書き方針を柔軟に設定。
  - Settings クラスを公開（settings）：
    - J-Quants / kabu / Slack / DB パス等のプロパティを提供（必須値は未設定時に ValueError）。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL のバリデーション。
    - duckdb/sqlite のパスは Path.expanduser を使用して正規化。

- AI 関連（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）で銘柄別センチメントを取得して ai_scores テーブルへ書き込む一連処理を実装。
    - ニュース対象ウィンドウ（JST基準）を calc_news_window で計算（前日 15:00 JST 〜 当日 08:30 JST、DB 比較は UTC naive datetime）。
    - バッチ処理（最大 20 銘柄/リクエスト）とテキストトリム（記事数・文字数の上限）によりトークン肥大を抑制。
    - レート制限（429）、ネットワーク断、タイムアウト、5xx サーバーエラーの共通再試行（指数バックオフ）を実装。
    - OpenAI の JSON Mode を想定したレスポンス検証とフォールバック処理（JSON 抽出、results の検証、コード照合、スコアの数値変換とクリップ）。
    - 書き込みは部分失敗を避けるため対象コードのみ DELETE → INSERT を行う冪等処理（DuckDB 互換性確保のため executemany の空リストを回避）。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF（1321）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
    - prices_daily / raw_news / market_regime を参照・更新する実装。
    - LLM 呼び出し（gpt-4o-mini）で JSON レスポンスを期待。API エラー時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等操作、失敗時には ROLLBACK を行い上位に例外を伝播。
    - ルックアヘッドバイアス対策：datetime.today()/date.today() を参照せず、prices_daily クエリは target_date 未満で制限。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー（market_calendar）を扱うユーティリティを実装。
    - 営業日判定 API: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - DB にカレンダーがない場合は曜日ベースでフォールバック（週末は非営業日）。
    - next/prev_trading_day は _MAX_SEARCH_DAYS による探索上限で無限ループを防止。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等的に更新。バックフィルや健全性チェックを実装。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを追加（取得数・保存数・品質問題・エラーの集約、to_dict を提供）。
    - 差分更新、バックフィル、品質チェック（quality モジュールとの連携）を想定したユーティリティ関数を実装。
    - DB テーブル存在チェックや最大日付取得などの内部ユーティリティを提供。
  - jquants_client との連携を想定した fetch/save ワークフローを実装（jquants_client は外部モジュールとして利用）。

- リサーチ / ファクター（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR）、Value（PER/ROE）などの計算関数を実装。
    - DuckDB のウィンドウ関数を利用して効率的に SQL ベースで計算。結果は (date, code) をキーとする dict のリストで返却。
    - データ不足時の挙動（必要行数未満は None）を明確化。
  - 特徴量探索ユーティリティ（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）：複数ホライズンを一度のクエリで取得。horizons のバリデーションを実装。
    - IC（Information Coefficient）計算（calc_ic）：Spearman のランク相関を実装（同順位は平均ランク）。
    - ランク変換ユーティリティ（rank）とファクター統計サマリー（factor_summary）を提供。
    - 外部ライブラリに依存せず標準ライブラリ + DuckDB で実装。

### 変更
- 設計上の注意点・ベストプラクティス（実装ポリシーとして明記）
  - すべての AI / スコア計算はルックアヘッドバイアスを防ぐために日時関数の自動参照を避け、target_date ベースで計算。
  - OpenAI 呼び出しはリトライや HTTP ステータスに基づく扱いを定義し、API エラー時は例外を投げずに安全にフォールバックする箇所を明確化（フェイルセーフ）。
  - DuckDB 互換性確保のため executemany に空リストを渡さない等の実装上の工夫。
  - モジュール間の結合を弱めるため、内部の API 呼び出しヘルパー関数（_call_openai_api 等）をモジュールごとに独立実装し、テストのためにモック差し替え可能に設計。

### 修正
- （初版のため既知のバグ修正履歴はなし）

### 非推奨
- （なし）

### 削除
- （なし）

### セキュリティ
- OpenAI API キー未設定時は ValueError を投げる明示的チェックを追加。自動的な秘密情報の漏洩を防ぐため、.env 読み込みはプロジェクトルートベースで制御。

---

注記:
- 本 CHANGELOG はコードベースの内容から機能と設計方針を推測してまとめたものです。実際のリリースノートや運用ルールに合わせて随時修正してください。