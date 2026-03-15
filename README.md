# KabuSys — 日本株自動売買システム

KabuSys は、日本株の自動売買を想定した軽量な Python パッケージのスケルトンです。  
モジュール化された設計（data / strategy / execution / monitoring）により、データ取得、売買シグナル生成、注文発行、監視・ログを分離して実装できます。

バージョン: 0.1.0

---

## プロジェクト概要

本リポジトリは、自動売買システムの基盤構造（パッケージ構成）を提供します。各機能は独立したサブパッケージとして整理されており、実際の取引APIやアルゴリズム、監視ツールは各サブパッケージ内に実装していく想定です。

主な目的:
- 明確なモジュール分割による拡張性の確保
- Strategy（戦略）と Execution（注文発行）の分離
- 監視／ロギング機能の独立

---

## 機能一覧（想定／拡張ポイント）

- データ取得（ヒストリカル、マーケットデータのストリーミング）
- テクニカル指標や特徴量の計算
- 売買シグナルの生成（複数戦略のプラグイン化を想定）
- 注文発行（証券会社APIへのラッパー）
- ポジション管理とリスク制御
- 監視・ログ収集（動作監視・アラートなど）
- バックテストの雛形（将来的な拡張）

※ 現在のコードベースはパッケージ構成のみで、個別機能は実装されていません。実運用には各サブモジュールの実装が必要です。

---

## セットアップ手順

前提:
- Python 3.8 以上（プロジェクトの要件に合わせて調整してください）
- Git（ソース取得用）

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository-root>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   # macOS / Linux
   source .venv/bin/activate
   # Windows (PowerShell)
   .venv\Scripts\Activate.ps1
   ```

3. pip の更新
   ```
   python -m pip install --upgrade pip
   ```

4. 依存パッケージのインストール
   - 現状 requirements.txt / pyproject.toml / setup.py が無い場合は、必要なライブラリ（例: requests, pandas, numpy 等）を個別にインストールしてください。
   - パッケージ形式が整っている場合は編集可能インストール:
     ```
     pip install -e .
     ```

5. （任意）テストや lint のセットアップ
   - pytest や flake8 / black などを追加して開発環境を整備してください。

---

## 使い方（例）

このパッケージはモジュール単位で拡張して使う想定です。現状は空のサブパッケージのみですが、以下のようなインターフェースを実装すると利用しやすくなります。

簡単な使用例（想定）:

```python
import kabusys

print("KabuSys version:", kabusys.__version__)

# 各モジュールの想定インターフェース例
from kabusys.data import DataLoader     # 実装するクラス
from kabusys.strategy import Strategy   # 実装するクラス
from kabusys.execution import Executor  # 実装するクラス
from kabusys.monitoring import Monitor  # 実装するクラス

# インスタンス化（引数やメソッド名は実装に合わせてください）
data_loader = DataLoader(api_key="xxx")
historical = data_loader.load_historical(symbol="7203.T", period="1d")

strategy = Strategy(params={})
signals = strategy.generate_signals(historical)

executor = Executor(api_credentials={"token": "yyy"})
for sig in signals:
    executor.execute_order(sig)

monitor = Monitor()
monitor.start()
```

推奨するメソッド名・役割（例）
- data.DataLoader
  - load_historical(symbol, start, end, interval)
  - stream_quotes(symbol, callback)
- strategy.Strategy
  - generate_signals(data) -> list[Signal]
  - update_parameters(...)
- execution.Executor
  - execute_order(order) -> OrderResult
  - cancel_order(order_id)
  - get_positions()
- monitoring.Monitor
  - start()
  - stop()
  - report(metric)

これらのクラスや関数は実装の自由度が高いですが、単体テストしやすいように副作用を小さくする設計（I/Oを抽象化する等）を推奨します。

---

## ディレクトリ構成

現在の最小構成（抜粋）:

- src/
  - kabusys/
    - __init__.py           - パッケージのエントリポイント（バージョン定義）
    - data/
      - __init__.py         - データ取得用サブパッケージ（実装を追加）
    - strategy/
      - __init__.py         - 戦略実装用サブパッケージ（実装を追加）
    - execution/
      - __init__.py         - 注文発行用サブパッケージ（実装を追加）
    - monitoring/
      - __init__.py         - 監視／ログ用サブパッケージ（実装を追加）

ルートに README.md（本ファイル）を置く想定です。将来的には以下のようなファイルが追加されます:
- pyproject.toml / setup.cfg / setup.py
- requirements.txt
- tests/
- examples/

---

## 開発・拡張ガイド

- モジュールの責務を明確に分離する（例: Strategy は注文発行を直接行わない）
- 外部 API との通信はインターフェースを抽象化してモック化/テスト可能にする
- 重要な機密情報（APIキー等）は環境変数や安全なシークレット管理を利用する
- ロギングは標準 logging モジュールを利用し、適切なログレベルを設定する
- 単体テスト（pytest 等）と CI（GitHub Actions 等）で品質を担保する

サンプルの実装方針:
1. data パッケージに DataLoader を実装し、ヒストリカルデータ取得を完成させる
2. strategy に 1〜2 個の戦略（例: 移動平均クロス）を実装
3. execution にブローカAPIラッパーを実装（テストはモックを使用）
4. monitoring に稼働モニタと簡易ダッシュボードを実装

---

## 貢献

改善やバグ報告、機能追加は歓迎します。Issue / Pull Request を作成してください。  
貢献ガイドライン（例）:
- フォーク → ブランチ作成 → コード修正 → テスト追加 → PR
- コードフォーマットは black、静的解析は flake8 を利用

---

## 注意事項

- 本レポジトリは基盤（スケルトン）を提供するもので、実際の売買に使う場合は十分な実装・検証・法的確認が必要です。  
- 実際の注文を発行するコードはテスト環境（サンドボックス）で十分に検証してください。損失リスクが伴います。

---

ライセンス: 適宜追加してください（例: MIT, Apache-2.0 など）。

---

作業を始める際に、必要であれば次のステップ（テンプレート実装のサンプルコード、CI 設定、requirements.txt の作成など）をこちらで提案できます。必要なら指示してください。