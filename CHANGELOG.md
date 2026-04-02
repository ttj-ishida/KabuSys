# Changelog

すべての変更は Keep a Changelog の慣習に従って記載しています。  
このプロジェクトは「初期リリース（0.1.0）」としての状態を反映しています。

4月 02, 2026 — 0.1.0
=====================

Added
-----
- パッケージの初期公開
  - パッケージメタ情報: バージョン `0.1.0` を設定。
  - __all__ による公開モジュール指定（data, strategy, execution, monitoring）。
- 環境設定管理
  - .env ファイルおよび環境変数から設定値を自動ロードするユーティリティを実装。
  - プロジェクトルート検出 ( .git / pyproject.toml ) による .env 自動読み込み（テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - 高度な .env パーサ実装: export 形式対応、シングル/ダブルクォートのエスケープ処理、インラインコメント判定、保護キー（OS 環境変数）の上書き制御。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB /監視 /システム設定等のプロパティを環境変数から取得（必須項目は未設定時に ValueError を送出）。
  - KABUSYS_ENV と LOG_LEVEL のバリデーション（許容値セット有り）、パス値は Path オブジェクトで返却。
- AI モジュール（kabusys.ai）
  - news_nlp モジュール: raw_news を集約して OpenAI（gpt-4o-mini, JSON Mode）で銘柄ごとのセンチメント(ai_score) を算出し ai_scores テーブルに保存する処理を実装。
    - タイムウィンドウ計算（JST ベース→UTC 変換）による記事選定。
    - 1銘柄あたりのトークン肥大化対策（記事数上限・文字数トリム）。
    - バッチ処理（最大 20 銘柄/コール）、JSON レスポンスの検証と ±1.0 でのクリップ、部分失敗に対する DB 書き換え保護（対象コードのみ DELETE → INSERT）。
    - リトライ戦略: 429、ネットワーク断、タイムアウト、5xx に対する指数バックオフリトライ。
    - フェイルセーフ設計: API 失敗時は該当チャンクをスキップして残りを処理。
  - regime_detector モジュール: ETF (1321) の 200 日移動平均乖離 (70%) とマクロニュースの LLM センチメント (30%) を合成し、市場レジーム（bull / neutral / bear）を日次で判定して market_regime テーブルへ保存。
    - MA200 比率計算（target_date 未満のデータのみを使用、ルックアヘッド防止）。
    - マクロキーワードによる raw_news フィルタリング（最大 20 件）。
    - OpenAI 呼び出し（gpt-4o-mini）によるマクロセンチメント評価、JSON パース、リトライ／フェイルセーフ処理。
    - 冪等性を考慮した DB 書き込み（BEGIN / DELETE / INSERT / COMMIT、障害時は ROLLBACK）。
    - API キー注入可能（引数優先、環境変数 OPENAI_API_KEY を使用）。
  - OpenAI 呼び出しは各モジュール内で独立実装し、テスト時に差し替え可能（ユニットテスト容易性を考慮）。
- Data モジュール（kabusys.data）
  - calendar_management: JPX カレンダー管理（market_calendar）と営業日判定ユーティリティ群を実装。
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - market_calendar が未取得のケースでは曜日ベース（週末を休日）でのフォールバックを提供。
    - DB 優先 → 未登録日は曜日フォールバックにより next/prev/get の一貫性を維持。
    - 夜間バッチ job (calendar_update_job): J-Quants からの差分取得、バックフィル、健全性チェック、保存（jq.save_market_calendar への委譲）。
  - ETL パイプラインインターフェース
    - ETLResult データクラスを公開（target_date / fetched/saved counts / quality issues / errors / ヘルパー属性）。
    - pipeline モジュールにて差分取得・保存・品質チェックの流れを設計（jquants_client・quality モジュールとの連携想定）。
    - DuckDB を前提とした実装。テーブル存在チェック・最大日付取得等のユーティリティを含む。
- Research モジュール（kabusys.research）
  - ファクター計算: calc_momentum, calc_value, calc_volatility を実装。
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
    - Value: raw_financials からの EPS/ROE 組合せによる PER/ROE 計算（未実装の指標は注記）。
    - Volatility: 20 日 ATR、相対ATR（atr_pct）、20 日平均売買代金、出来高比率。
    - DuckDB のウィンドウ関数を活用した SQL ベース実装（外部 API 不使用）。
  - 特徴量探索: calc_forward_returns, calc_ic, factor_summary, rank を提供。
    - Forward returns: 任意ホライズン（デフォルト [1,5,21]）に対する LEAD ベースのリターン計算。
    - IC: スピアマンランク相関の実装（ランク処理は同順位を平均ランクで扱う）。
    - 統計サマリー: count/mean/std/min/max/median を標準ライブラリで算出。
  - 研究ユーティリティは外部ライブラリ（pandas 等）に依存しない設計。
- ロギングとエラーハンドリング
  - 各モジュールで詳細な logger 呼び出しを追加（info/debug/warning/exception）。
  - API エラーやパース失敗はログに残してフェイルセーフ（処理継続）する方針を採用。

Changed
-------
- 初期版ため該当なし（新規実装）。

Fixed
-----
- 初期版ため該当なし。

Removed
-------
- 初期版ため該当なし。

Security
--------
- 初期版ため該当なし。

Known limitations / Notes
-------------------------
- 一部モジュールは外部クライアント（jquants_client, jq.save_market_calendar 等）に依存しており、実行にはそれらの実装が必要。
- OpenAI API を利用する機能は API キー（OPENAI_API_KEY）が必須。テストのために api_key を引数経由で注入可能。
- DuckDB を前提に SQL を記述しているため、別の DB を使う場合は移植が必要。
- news_nlp と regime_detector は JSON Mode を前提としたレスポンス処理を行うが、LLM の応答のゆらぎに対する復元ロジック（外側の {} 抽出等）を含む。
- パッケージ __all__ の公開対象に ai / research が含まれていない箇所があり、ユーザが意図する公開 API と実装の同期に注意が必要（将来的な整理を推奨）。
- pipeline.py の末尾に処理途中で切れたような箇所（truncated）を検出。実装ファイルが完全でない可能性があるため、パイプライン周りの最終実装は確認・補完が必要。

開発者向けメモ
---------------
- テスト容易性を考慮して OpenAI 呼び出し関数はモジュール内で定義しており、unittest.mock.patch による差し替えが可能。
- .env パーサは実務でよくあるケース（export 付き、クォート/エスケープ、インラインコメント）に対応済み。
- ルックアヘッドバイアス防止のため、target_date を受け取り date.today()/datetime.today() を参照しない設計方針を各所で徹底。

今後の予定（短期）
------------------
- pipeline モジュール末尾の不完全箇所の修正・補完。
- パッケージの公開 API 整理（__all__ を実装内容と整合させる）。
- ドキュメントの追加（使用例、DB スキーマ、jquants_client の仕様、実行手順）。
- 単体テスト／統合テストの整備（OpenAI 呼び出しモック、DuckDB のテストデータセット）。

署名
----
この CHANGELOG はコードベースの現状から推測して作成しています。実際の実装・外部依存・リリース方針に合わせて適宜更新してください。