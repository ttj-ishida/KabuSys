CHANGELOG
=========
すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルはパッケージの主要なリリースや機能追加・修正の概要を示します。

[Unreleased]
------------

- （現時点のベースは初期リリースです。次回リリースでここに変更を記載します）

[0.1.0] - 2026-04-03
--------------------

初回公開リリース。本プロジェクトは日本株のデータ取得・特徴量計算、AI を利用したニュースセンチメント評価、
および市場レジーム判定を行う自動売買/リサーチ基盤として以下の機能を提供します。

追加（Added）
- パッケージ基本情報
  - kabusys パッケージ初期実装（__version__ = 0.1.0）。
  - パッケージ公開 API（data, strategy, execution, monitoring を __all__ でエクスポート）。

- 環境設定管理（kabusys.config）
  - .env / .env.local ファイル自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途）。
  - 既存 OS 環境変数の保護（protected set）を実装し .env.local による上書き挙動を制御。
  - Settings クラスを提供し、J-Quants / kabu ステーション / LINE / DB パス /監視等の設定プロパティを公開。
  - KABUSYS_ENV や LOG_LEVEL の検証（許容値チェック）と is_live / is_paper / is_dev 判定プロパティを実装。

- AI モジュール（kabusys.ai）
  - news_nlp: ニュース記事群を銘柄別に集約し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信して
    銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ計算（JST基準 → UTC変換）calc_news_window を提供。
    - バッチ処理（最大20銘柄/チャンク）、1銘柄あたり記事数・文字数制限によるトリミング。
    - API レスポンスの厳密なバリデーションとスコアの ±1.0 クリップ。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフとリトライ。
    - テスト容易性を考慮し OpenAI 呼び出し箇所を差し替え可能に実装（ユニットテスト用 patch を想定）。
  - regime_detector: ETF(1321) の 200 日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を合成して
    日次の market_regime を算出・書き込みする機能を実装。
    - ma200_ratio の計算（ルックアヘッド防止のため target_date 未満のみ使用）。
    - マクロキーワードで raw_news をフィルタして LLM に渡すロジック。
    - OpenAI 呼び出しのリトライ/フェイルセーフ（API 失敗時は macro_sentiment=0.0 を採用）。
    - 冪等的な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）、失敗時は ROLLBACK の試行とログ。

- データ基盤（kabusys.data）
  - calendar_management: JPX カレンダー管理（market_calendar）と営業日判定ユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar の未取得時は曜日ベース（週末除外）でフォールバックする一貫性ある振る舞い。
    - 夜間バッチ calendar_update_job を実装（J-Quants から差分取得・バックフィル・健全性チェック・保存）。
  - pipeline / ETL: ETL パイプラインの骨格と ETLResult を実装。
    - 差分取得、保存、品質チェック（quality モジュール連携）を想定した設計。
    - ETLResult（dataclass）による実行レポート（品質問題・エラー一覧の集約）を提供。
  - jquants_client 経由の idempotent 保存、品質チェックとの連携を想定した実装方針。

- リサーチ（kabusys.research）
  - factor_research: ファクター計算（Momentum / Volatility / Value / Liquidity の主要指標）を実装。
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均出来高・売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務を取得し PER, ROE を計算。
    - すべて DuckDB 上の SQL を用いた実装で、外部サービスにアクセスしない設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。
    - rank / factor_summary: ランク付けユーティリティと統計サマリーを提供。
    - 外部ライブラリに依存せず標準ライブラリと DuckDB のみで実装。

修正（Fixed） / 安全性強化（Security）
- .env パーサの堅牢化
  - export プレフィックス対応、クォート内エスケープ処理、インラインコメントの取り扱いを実装。
  - 不正な行は無視することで読み込みの堅牢性を向上。
- DB 操作の堅牢化
  - 複数テーブル書き換えはトランザクションで囲み、例外発生時は ROLLBACK を試行してログ出力。
  - ai_scores 更新では部分失敗時に既存スコアを保護するため、対象コードだけを DELETE → INSERT する方式を採用。
  - DuckDB のバージョン差異（executemany の空リスト扱い等）への対処を明示。
- LLM / API 呼び出しのフォールバック
  - OpenAI 呼び出しで JSON 解析失敗や API エラーが発生した場合、システムは例外を投げずフェイルセーフなデフォルト（例: macro_sentiment=0.0）を用いる設計を採用。
- ルックアヘッドバイアス対策
  - 各種スコア計算やウィンドウ定義で datetime.today() / date.today() を参照しない設計方針を徹底（外部から target_date を注入して determinism を担保）。

ドキュメント（Documentation）
- 各モジュールに設計方針・処理フロー・入力/出力仕様を詳細に記載（モジュールトップの docstring）。
- テスト容易性に関する注記（OpenAI 呼び出しの差し替え、KABUSYS_DISABLE_AUTO_ENV_LOAD）を明記。

破壊的変更（Removed）
- なし（初回リリース）

非推奨（Deprecated）
- なし（初回リリース）

セキュリティ（Security）
- API キーは引数で注入可能かつ環境変数（OPENAI_API_KEY など）から解決する方式。未設定時は明確な ValueError を送出。
- 環境変数読み込みは OS 環境変数を保護する設計（.env による意図しない上書きを防止）。

補足
- この CHANGELOG はコードベースから推測して作成しています。実際のコミット履歴・リリースノートと差分がある可能性があります。実際のリリース日やマイナー変更の詳細はリポジトリのタグ／コミットログを参照してください。