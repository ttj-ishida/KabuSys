# TODO: KabuSys 運用UI（ダッシュボード）の設計と実装

> **ステータス: 実装完了**（Issue #231）  
> 実装: `src/kabusys/monitoring/streamlit_dashboard.py`（Home/System Status）、`pages/2_Signal_Queue.py`、`pages/3_Performance.py`、`pages/4_Strategy_Lab.py`、`pages/1_WebManual.py`  
> 拡張計画: `TODO_StreamlitOperationsExpansion.md` 参照。

## 1. 背景と目的
現在、KabuSysの運用状態を確認するためにはログファイルやDBを直接参照する必要があり、直感的な全体像の把握が難しい状態である。
システムを安全かつ効率的に監督するため、すべての運用情報を1つの画面に集約する「運用ダッシュボード（Operations UI）」を構築する。

## 2. アーキテクチャ要件（決定事項）

*   **技術スタック**: `Streamlit`
    *   採用理由: Pythonのみで迅速にデータダッシュボードを構築でき、DuckDBやPandasデータフレームの可視化と極めて相性が良いため。
*   **セキュリティとアクセス元**: `ローカルPC（localhost）専用`
    *   採用理由: このUIはKabuSysが稼働しているWindows PC上で直接立ち上げ、ブラウザで確認する想定とする。外部ネットワークからのアクセスは想定しないため、ログイン認証等の複雑なセキュリティ実装は不要とする。

## 3. 画面構成（ビュー）要件

Streamlitのマルチページ機能（`pages/`）を利用し、時間帯別の運用作業に合わせた以下の4つのビューを構築する。

1.  **🏠 Home / System Status (全体ステータス)**
    *   API接続状態、Kill Switch発動状態、稼働フェーズの表示
    *   直近の `ERROR` / `CRITICAL` ログのリアルタイム表示
    *   物理アクションボタン（Emergency Stop / Restart 等 ※要確認ダイアログ）
2.  **🌅 Pre-Market Check (朝の確認ビュー)**
    *   昨晩の夜間バッチ結果の成否サマリ
    *   本日発注予定のシグナルリスト（Signal Queue）と想定投下金額
    *   運用開始可否の総合判定（READY / BLOCKED）
3.  **📈 Intraday Monitor (ザラ場監視ビュー)**
    *   本日のリアルタイム・ドローダウン状況
    *   発注済み注文のステータス一覧（約定、エラー弾かれ等）
    *   システムと証券口座間のポジション差分チェック結果（Position Reconciliation）
4.  **🌙 Market Close & Performance (引け後・成績ビュー)**
    *   当日の実現損益（P&L）サマリ
    *   引け時点での全保有銘柄リストと含み損益
    *   現金残高とキャッシュ比率（翌日への持ち越し余力）

## 4. 実装TODOリスト

- [ ] `requirements.txt` または `pyproject.toml` に `streamlit` を追加
- [ ] 運用UI用ディレクトリの作成（`src/kabusys/ui/`）
- [ ] エントリーポイント `app.py`（Home画面）の実装
- [ ] マルチページ構成の作成
  - [ ] `src/kabusys/ui/pages/01_pre_market.py` の実装
  - [ ] `src/kabusys/ui/pages/02_intraday.py` の実装
  - [ ] `src/kabusys/ui/pages/03_market_close.py` の実装
- [ ] 共通コンポーネントの作成
  - [ ] DBからデータをロードするデータフェッチャー関数の共通化
  - [ ] ログをパースしてDataframe化するモジュール
- [ ] 各画面のReadOnly（表示）機能の完成
- [ ] （オプション）アクションボタン（Kill Switch等）の実装

## 5. 起動方法（想定）
```powershell
# プロジェクトルートで実行
streamlit run src/kabusys/ui/app.py
```
