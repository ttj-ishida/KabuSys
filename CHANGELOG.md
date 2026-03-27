CHANGELOG
=========

この CHANGELOG は Keep a Changelog の形式に準拠しており、すべての重大な変更を追跡します。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- なし

[0.1.0] - 2026-03-27
---------------------

Added
- 初期リリース。パッケージ kabusys の基本機能を実装。
  - パッケージ初期化
    - src/kabusys/__init__.py にてバージョンを "0.1.0" として定義し、主要サブパッケージ（data, research, ai 等）を公開。
  - 環境設定 / .env 管理
    - src/kabusys/config.py
      - .env/.env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）。
      - export KEY=val 形式・クォート/エスケープ・インラインコメント対応の行パーサを実装。
      - 自動ロードの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）をサポート。
      - 必須環境変数取得時に ValueError を投げる _require ユーティリティと Settings クラスを提供。
      - 設定項目: J-Quants / kabuステーション / Slack / DB パス（DuckDB/SQLite）/実行環境・ログレベル判定（development/paper_trading/live、LOG_LEVEL の検証）。
  - AI（ニュース NLP / レジーム判定）
    - src/kabusys/ai/news_nlp.py
      - ニュース記事を銘柄毎に集約し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信してセンチメント（-1.0〜1.0）を算出。
      - タイムウィンドウ（前日15:00 JST〜当日08:30 JST）計算ユーティリティ（calc_news_window）。
      - バッチサイズ、文字数・記事数トリム、JSON レスポンスの堅牢なバリデーション、±1.0 クリップ、部分書き換え（DELETE→INSERT）による冪等性を考慮した ai_scores への書き込み。
      - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフとリトライ実装。API エラーはフェイルセーフでスキップし続行。
    - src/kabusys/ai/regime_detector.py
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
      - DuckDB を用いた ma200_ratio 計算、マクロキーワードによるニュース抽出、OpenAI 呼び出し（gpt-4o-mini）・リトライ戦略、スコア合成、market_regime への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
      - API 失敗時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ設計。
  - データプラットフォーム（Data）
    - src/kabusys/data/calendar_management.py
      - JPX カレンダー管理、営業日判定、前後の営業日取得、期間内営業日列挙、SQ 日判定、夜間バッチ更新ジョブ（calendar_update_job）を実装。
      - market_calendar が未取得または不完全な場合の曜日ベースフォールバック、最大探索日数制限、バックフィル・健全性チェックを実装。
    - src/kabusys/data/pipeline.py / etl.py
      - ETLResult データクラス（ETL の実行結果を集約）を定義し、ETL の差分取得・保存・品質チェックのインターフェース設計を用意。
      - jquants_client 経由での差分フェッチと冪等保存を想定した設計、品質チェック（quality モジュール）との連携を想定。
    - src/kabusys/data/__init__.py, src/kabusys/data/etl.py
      - public API の整理（ETLResult の再エクスポート等）。
  - リサーチ（ファクター計算・特徴量探索）
    - src/kabusys/research/factor_research.py
      - Momentum（1M/3M/6M リターン, ma200 乖離）、Volatility（20 日 ATR, 相対 ATR）、Liquidity（20 日平均売買代金・出来高比率）、Value（PER, ROE）を DuckDB の prices_daily/raw_financials を基に計算する関数を提供。
      - データ不足時の None 扱い、営業日スキャン範囲バッファ、結果を (date, code) キーの辞書リストで返す設計。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算（任意ホライズン）、Spearman ランク相関（IC）計算、ランク生成ユーティリティ、ファクター統計サマリー（count/mean/std/min/max/median）を実装。外部依存無しで動作。
  - その他ユーティリティ
    - src/kabusys/ai/__init__.py, src/kabusys/research/__init__.py
      - 主要関数の公開（__all__ による整理）。
    - テスト容易性を考慮し、OpenAI 呼び出しを差し替え可能（内部の _call_openai_api を unittest.mock.patch で置換可能）に実装。

Changed
- 該当なし（初期リリース）。

Fixed
- 該当なし（初期リリース）。

Security
- 環境変数の読み込みに関して、既存 OS 環境変数を保護する設計（.env を上書きしない既定の動作、override/ protected 引数）を導入。
- 必須シークレット（OpenAI / Slack / Kabu API 等）未設定時は明示的に ValueError を投げることで安全な失敗を促進。

Notes / 設計上の留意点
- ルックアヘッドバイアス対策: 日付計算に datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計を徹底。
- DuckDB をデータレイヤに採用。DuckDB のバージョン差異（executemany の空リスト扱い等）に配慮した実装（空パラメータチェック等）。
- OpenAI 呼び出しは JSON mode を利用し、レスポンス整形や部分的な非整合に対して堅牢性を高めるためのパース・バリデーションを実装。
- API 呼び出しの冗長性（リトライ / バックオフ）を多くの箇所で採用し、外部サービス障害の影響を限定する設計。

開発者向けメモ
- 自動 .env 読み込みはパッケージ配布後でも動作するように __file__ を基準にプロジェクトルートを探索。テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動読み込みを無効化可能。
- OpenAI クライアントの注入（api_key 引数）を各スコアリング関数で受け付け、テスト時に環境変数に依存しないように設計している。

今後の予定（例）
- ファクターの追加（PBR、配当利回り等）
- モデル学習用の特徴量生成パイプライン統合
- ETL の逐次実行・スケジューラ統合（より細かなフェイルオーバー処理）
- モニタリング／アラート機能（Slack 連携の利便性向上）