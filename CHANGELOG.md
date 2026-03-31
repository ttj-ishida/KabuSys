CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。
リリースは安定版のためセマンティックバージョニングを使用します。

Unreleased
----------

（なし）

0.1.0 - 2026-03-31
-----------------

Added
- 基本パッケージとバージョニング
  - パッケージ定義: kabusys パッケージを追加。バージョンは 0.1.0。（src/kabusys/__init__.py）

- 環境変数・設定管理
  - Settings クラスを実装し、アプリケーション設定を環境変数から取得するプロパティを公開。
    - J-Quants / kabuステーション / Slack / データベース（DuckDB, SQLite）/ システム設定（環境・ログレベル）をサポート。（src/kabusys/config.py）
  - .env ファイル自動読み込み機能の実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - 環境変数で無効化可能: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサを堅牢化:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - クォートなしの値に対するインラインコメント処理（直前が空白/タブの '#' をコメントと判定）
    - 読み込み失敗時の警告、保護された OS 環境変数の上書き制御（protected set）

- AI（自然言語処理）モジュール
  - ニュースセンチメントスコアリング機能（news_nlp）
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）にバッチ送信して銘柄単位のスコアを取得、ai_scores テーブルへ書き込む。（src/kabusys/ai/news_nlp.py）
    - 特徴:
      - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を正確に計算（UTC 変換）
      - 1銘柄あたりの記事上限（件数・文字数）を設定してトークン肥大化を抑制
      - 最大 _BATCH_SIZE（20）銘柄ごとのチャンク送信
      - JSON Mode を利用しレスポンスを厳密な JSON として検証
      - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ
      - レスポンス検証（results 配列、code/score の型チェック、未知コード無視、数値性と有限性チェック）
      - スコアは ±1.0 にクリップ
      - DuckDB の executemany 空リスト問題に配慮して書き込み時のガード実装
      - テスト容易性のため API 呼び出し抽象化（_call_openai_api をパッチ可能）

  - 市場レジーム判定機能（regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出し、market_regime テーブルへ冪等書き込みを行う。（src/kabusys/ai/regime_detector.py）
    - 特徴:
      - ma200_ratio の計算は target_date 未満のデータのみを使用しルックアヘッドバイアスを防止
      - マクロニュースはキーワードフィルタ（日本語・英語の主要マクロ用語）で抽出し LLM に評価させる
      - OpenAI 呼び出しはリトライ・フェイルセーフ（失敗時は macro_sentiment = 0.0）
      - スコア合成と閾値によるラベル付与、DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等処理
      - API キーは引数で注入可能（テスト向け）または OPENAI_API_KEY を参照

- データプラットフォーム関連
  - マーケットカレンダー管理（calendar_management）
    - market_calendar テーブルを利用した営業日判定・次/前営業日取得・期間の営業日一覧取得・SQ判定などのユーティリティを実装（フォールバックとして曜日ベース判定をサポート）。（src/kabusys/data/calendar_management.py）
    - calendar_update_job を実装し、J-Quants API から差分取得して market_calendar を冪等保存・バックフィルを行う設計
    - エッジケース対策（最大探索日数、健全性チェック、NULL 値検出時の警告）

  - ETL パイプライン（pipeline, etl）
    - ETLResult データクラスを追加し ETL の実行結果（取得件数、保存件数、品質チェック結果、エラー）を一元管理するインターフェースを提供。（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - 差分更新、バックフィル、品質チェックの設計説明を含む

  - jquants_client と品質チェックモジュールとの連携を想定した設計方針の実装（関数呼び出しや保存のエラーハンドリングを強化）

- リサーチ / ファクター計算
  - factor_research: モメンタム / ボラティリティ / バリュー系ファクターを実装（calc_momentum, calc_volatility, calc_value）。prices_daily / raw_financials を参照し DuckDB 上で計算。欠損やデータ不足の扱いを明確化。（src/kabusys/research/factor_research.py）
    - モメンタム: 1M/3M/6M リターン、200日MA乖離（データ不足時は None）
    - ボラティリティ: 20日 ATR, ATR/price, 20日平均売買代金、出来高比率
    - バリュー: PER（EPS が 0/欠損なら None）、ROE（raw_financials の最新値を使用）
  - feature_exploration: 将来リターン計算(calc_forward_returns)、IC（Spearman rank）計算(calc_ic)、ランク化ユーティリティ(rank)、統計サマリー(factor_summary) を実装。外部ライブラリを使わず標準ライブラリのみで実装。（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns は任意ホライズン対応（デフォルト [1,5,21]）、入力検証あり
    - calc_ic は ties を考慮したランク処理とスピアマン ρ 計算、データ不足時は None を返す
    - factor_summary は count/mean/std/min/max/median の算出

- モジュール公開インターフェース整理
  - ai、research、data パッケージの __init__ で主要関数を再エクスポートし使いやすく整理
  - etl モジュールで pipeline.ETLResult を再エクスポート

Changed
- 設計方針の明示
  - 多くのモジュールで「ルックアヘッドバイアスを防ぐため datetime.today()/date.today() を直接参照しない」設計が採用され、target_date を明示的に受け取る API 形に統一。

Fixed
- DuckDB に関する互換性考慮
  - executemany に空リストを渡せない DuckDB 0.10 系の挙動に対応するガードを追加（params の空チェック）。

Security
- 機密情報の取扱い
  - 各種 API キーやトークン（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）は環境変数から取得する設計。Settings._require は未設定時に ValueError を送出して検出を容易にする。

Notes / Known issues
- OpenAI 呼び出しは外部サービスに依存するため、API の仕様変更やレート制限により挙動が変わる可能性がある。テストでは _call_openai_api をパッチしてモック化することを想定。
- news_nlp/regime_detector の JSON パースは回復処理を入れているが、LLM レスポンスのフォーマット逸脱により一部スコアが欠落する場合がある（その場合は当該銘柄/日をスキップ）。
- calendar_update_job は J-Quants クライアント（jquants_client）の実装に依存する。外部 API エラーはログ出力のうえ 0 を返すフェイルセーフ実装。

Documentation
- 各モジュール冒頭に設計方針・処理フロー・注意点のドキュメンテーションを多数追加。関数ドキュメンテーション（docstring）により振る舞い・引数・戻り値・例外が明確化されている。

---- 

今後の予定（例）
- AI モデル切替やプロンプト改善によるスコア品質向上
- jquants_client のインターフェース実装とそれに伴う統合テスト
- モニタリング・Slack 通知など実行/監視系モジュールの追加拡張

（変更点はコードから推測して記載しました。実際のリリースノートはコミット履歴や PR をもとに調整してください。）