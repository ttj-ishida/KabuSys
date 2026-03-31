# Changelog

すべての重要な変更はこのファイルに記載します。  
フォーマットは Keep a Changelog に準拠しています。  

全ての日付はリリース日を示します。

## [Unreleased]
- （現在のリポジトリ状態はバージョン 0.1.0 として初回リリースに相当します。今後の変更はこちらに記載してください）

## [0.1.0] - 2026-03-31
最初の公開リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - src/kabusys/__init__.py を追加し、パッケージ名と公開モジュール一覧を定義（version=0.1.0）。
- 設定・環境変数管理
  - src/kabusys/config.py
    - .env ファイルや環境変数から設定を自動ロードする機能を実装（プロジェクトルート検出: .git または pyproject.toml を探索）。
    - .env のパース機能を細かく実装（export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメント処理）。
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を導入（テスト時の挙動制御）。
    - OS 環境変数を保護する protected 機構、.env / .env.local の読み込み優先度を実装。
    - 必須設定の取得ヘルパー（_require）と Settings クラスを提供（J-Quants / kabuステーション / Slack / DB パス / 環境判定 / ログレベル等）。
    - KABUSYS_ENV と LOG_LEVEL 値検証を実装（許容値チェック）。
- AI（Natural Language）関連
  - src/kabusys/ai/news_nlp.py
    - ニュース記事を銘柄毎に集約し、OpenAI（gpt-4o-mini）を使ってセンチメントスコアを算出する score_news を実装。
    - バッチ処理（最大 20 銘柄/回）、トークン肥大化対策（記事数・文字数トリム）、JSON Mode を用いた出力バリデーションを実装。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ、失敗時のフェイルセーフ挙動（スキップ）を実装。
    - DuckDB への冪等書き込み（対象コードのみ DELETE → INSERT）により部分失敗時の保護を行う。
    - calc_news_window 関数を提供（JST の前日 15:00 〜 当日 08:30 を UTC に変換）。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成して日次で市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - マクロ記事抽出、OpenAI 呼び出し（gpt-4o-mini）による macro_sentiment 計測、スコア合成ロジック（重み付け: MA 70% / マクロ 30%）、閾値判定を実装。
    - API 呼び出しのリトライ・エラー対処、レスポンスパース失敗時のフォールバック（macro_sentiment=0.0）を実装。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
  - 共通設計方針: datetime.today()/date.today() を直接参照せず、ターゲット日を明示的に受け取ることでルックアヘッドバイアスを防止。
  - テストしやすさのため、OpenAI 呼び出しポイントはモジュール内で関数化して差し替え可能に実装。
- データ（Data Platform）
  - src/kabusys/data/pipeline.py, src/kabusys/data/etl.py, src/kabusys/data/__init__.py
    - ETL のための ETLResult データクラスを定義（取得数、保存数、品質問題、エラー等の集約）。
    - 差分更新・バックフィル・品質チェックのためのユーティリティ関数と設計方針を実装。
    - DuckDB のテーブル存在確認や最大日付取得などのヘルパー実装。
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理機能を実装（market_calendar テーブルの参照／更新、営業日判定、next/prev_trading_day、get_trading_days、is_sq_day）。
    - カレンダーデータがない場合の曜日ベースフォールバック、最大探索日数制限、バックフィル戦略を含む夜間バッチ処理 calendar_update_job を実装。
    - jquants_client 経由での取得・保存（外部クライアントモジュールに依存）を想定した設計。
- リサーチ（Research）
  - src/kabusys/research/factor_research.py
    - ファクター計算（モメンタム、ボラティリティ、バリュー）関数を実装:
      - calc_momentum: 1M/3M/6M リターン、200日MA乖離（データ不足時は None）
      - calc_volatility: 20日ATR、相対ATR、20日平均売買代金、出来高比率
      - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を計算
    - DuckDB SQL を活用し、prices_daily / raw_financials のみ参照する安全な実装。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 指定ホライズンの将来リターン計算（horizons 引数、入力検証あり）。
    - calc_ic: スピアマンのランク相関（IC）計算（None の除外、最小サンプル数チェック）。
    - rank: 同順位（ties）は平均ランクで処理するランク化ユーティリティ。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）計算ユーティリティ。
  - src/kabusys/research/__init__.py で上記関数を再エクスポート。
- その他
  - ロギングを広範に導入し、各処理の実行状況・警告・エラーを出力。
  - DuckDB を主な永続ストアとして想定した SQL 実装と互換性配慮（ex. executemany の空リスト回避、list バインドの問題回避）。

### Changed
- （初回リリースのためなし）

### Fixed
- （初回リリースのためなし）

### Security
- OpenAI API キーは引数注入または環境変数 OPENAI_API_KEY を使用。未設定時は明示的に ValueError を送出して誤使用を防止。

### Notes / Design decisions
- ルックアヘッドバイアス回避: すべての分析/スコアリング関数は target_date を引数に取り、内部で現在時刻を参照しない設計になっています。
- フェイルセーフ性: 外部 API の障害や非致命的なデータ問題が発生しても全体処理が停止しない（可能な限りスキップして継続）よう設計しています。
- DuckDB との互換性を考慮し、SQL と Python の組合せで計算・書き込み・検証を行っています。

---

今後のリリースでは、テストケース追加、jquants_client 実装の統合、監視・実行（execution / monitoring）モジュールの実装強化、パフォーマンス最適化などを想定しています。